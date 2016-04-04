# user.location = ['ingame', 'kicked', 'searching', 'finished', 'outgame']
# player.state = ['alive', 'dead']

import redis
import uuid
import json
import weakref
import inspect
import ast          # converts simple JSON string to python dict through ast.eval
import warnings
from pympler import muppy
from pympler import summary

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

from tornado.ioloop import PeriodicCallback, IOLoop
from swampdragon.pubsub_providers.data_publisher import publish_data

import werewolves_game.server_scripting as wwss
from werewolves_game.server_scripting.redis_util import *



class User:
    # user specific functions pertaining to general usage (login, cookies etc.)

    def __init__(self, p_id=None, session_key=None):
        self.name = ""
        self.g_history = []	# list of games just been in to assist matchmaking algorithm
        self.location = ""
        self.session_key = ""
        self.broadcastable = []

        self.broadcastable.extend(["name", "location", "p_id"])

        # look for p_id in session
        if session_key:
            self.session = SessionStore(session_key=session_key)
            self.session_key = session_key
            if 'p_id' in self.session:
                p_id = self.session['p_id']

        try:
            # try loading from redis
            self.p_id = p_id
            self.load(p_id)
        except Exception as error:
            print("couldn't load user's p_id from redis: "+str(error))
            print("putting in default values")

            self.name = "Richard"
            self.p_id = str(uuid.uuid4())
            self.location = "outgame"
            self.session = SessionStore(self.session_key)
            self.session_key = self.session.session_key

            self.session['p_id'] = self.p_id
            self.session['location'] = self.location
            self.session.save()

            self.save()

        print("user initialised and saved: "+self.p_id)

    def __eq__(self, other):
        return self.p_id == other.p_id

    def load(self, p_id, redis_player=None):
        if not redis_player:
            redis_player = ww_redis_db.hgetall("player_list:"+str(p_id))
            redis_player = {k.decode('utf8'): v.decode('utf8') for k, v in redis_player.items()}

        if len(redis_player) == 0:
            raise Exception("no redis player found")
            return False

        self.p_id = p_id
        self.session_key = redis_player['session_key']
        self.session = SessionStore(session_key=self.session_key)
        self.location = redis_player['location']
        self.name = redis_player['name']
        self.g_history = (redis_player['g_history']).split("|")
        
        return True

    def save(self):
        ww_redis_db.hset("player_list:"+self.p_id, "session_key", self.session_key)
        ww_redis_db.hset("player_list:"+self.p_id, "name", self.name)
        ww_redis_db.hset("player_list:"+self.p_id, "location", self.location)
        ww_redis_db.hset("player_list:"+self.p_id, "g_history", ("|").join(self.g_history))

    def as_JSON(self, user_json={}, attribute_filter=[]):
        if not attribute_filter or 'p_id' in attribute_filter:
            user_json['p_id'] = self.p_id

        if not attribute_filter or 'name' in attribute_filter:
            user_json['name'] = self.name

        return json.dumps(user_json, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    # redundant
    def push_message(self, **kwargs):
        data_dict = {}
        channel = ""

        if 'msg' not in kwargs or 'groups' not in kwargs:
            return

        if (	'game' in kwargs['groups'] and
                'g_id' in self.session and
                'location' in self.session and
                self.session['location'] == "ingame"
            ):
            channel = 'game:'+self.session['g_id']
        elif 'player' in kwargs['groups'] and 'p_id' in kwargs:
            channel = 'player:'+kwargs['p_id']

        data_dict['message'] = kwargs['msg']
        data_dict['channel'] = channel

        publish_data(channel, data_dict)
        return data_dict

    def give_message(self, msg, sender, target, time):
        data_dict = {}
        channel = "player:"+self.p_id

        data_dict['message'] = msg
        data_dict['sender'] = sender
        data_dict['target'] = target
        data_dict['time'] = time
        data_dict['channel'] = channel
        data_dict['type'] = "message"

        publish_data(channel, data_dict)
        return data_dict

class Player(User):
    # game specific class for interacting with the game class (join, interact with other players generally)

    def __init__(self, p_id=None, session_key=None):
        # overridable default attributes
        self.character = "unassigned"
        self.state = "alive"
        self.knows_about = {}

        if not p_id and not session_key:
            raise ValueError("neither p_id or session_key supplied!")

        if session_key:
            super().__init__(session_key=session_key)
        else:
            super().__init__(p_id=p_id)

        self.knows_about[self.p_id] = None
        self.broadcastable.extend(["character", "state"])
        

    def __del__(self):
        self.save()	# not guaranteed to be called!

    def __eq__(self, other):
        return self.p_id == other.p_id

    def load(self, p_id):
        redis_player = ww_redis_db.hgetall("player_list:"+str(p_id))
        redis_player = {k.decode('utf8'): v.decode('utf8') for k, v in redis_player.items()}

        # should always be true
        if 'character' in redis_player:	# can be rewritten with all() keyword http://stackoverflow.com/questions/8041944/if-x-and-y-in-z
            self.character = redis_player['character']
        if 'state' in redis_player:
            self.state = redis_player['state']
        if 'knows_about' in redis_player:
            redis_knows_about_dict = ast.literal_eval(redis_player['knows_about'])
            self.knows_about = redis_knows_about_dict

        # optional
        if 'g_id' in redis_player:
            self.g_id = redis_player['g_id']
            print("game added as weak ref for Player")
            #self.game = Game(g_id)

        return super().load(p_id, redis_player)

    def save(self):
        super().save()
        ww_redis_db.hset("player_list:"+self.p_id, "state", self.state)
        ww_redis_db.hset("player_list:"+self.p_id, "character", self.character)

        ww_redis_db.hset("player_list:"+self.p_id, "knows_about", self.knows_about)

        if hasattr(self, 'g_id'):
            ww_redis_db.hset("player_list:"+self.p_id, "g_id", self.g_id)

    def as_JSON(self, player_json={}, attribute_filter=[]):
        super().as_JSON(player_json, attribute_filter)

        if not attribute_filter or 'character' in attribute_filter:
            player_json['character'] = self.character

        if not attribute_filter or 'state' in attribute_filter:
            player_json['state'] = self.state

        return json.dumps(player_json, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    # adds information on another player's attributes
    def gain_info(self, attribute_filter, p_id=None, info_player=None, gain_all=False):
        # error checking
        if not p_id and not info_player:
            raise ValueError("Either p_id or player needs to be supplied")

        if not p_id and info_player and not isinstance(info_player, Player):
            raise ValueError("supplied player argument must be a Player")

        if not p_id and info_player:
            p_id = info_player.p_id

        # set knows about to empty list
        if p_id not in self.knows_about:
            if attribute_filter:
                self.knows_about[p_id] = []

        # attribute_filter with None allows everything to be broadcasted
        if gain_all or attribute_filter is None:
            self.knows_about[p_id] = None
        else:
            for attribute in attribute_filter:
                if attribute not in self.broadcastable:
                    raise ValueError("Attribute '"+attribute+"' is not a broadcastable attribute.")
                elif attribute not in self.knows_about[p_id]:
                    self.knows_about[p_id].append(attribute)

        self.save()

    def lose_info(self, attribute_filter, p_id=None, info_player=None, lose_all=False):
        # error checking
        if not p_id and not info_player:
            raise ValueError("Either p_id or player needs to be supplied")

        if not p_id and info_player and not isinstance(info_player, Player):
            raise ValueError("supplied player argument must be a Player")

        if not p_id and info_player:
            p_id = info_player.p_id

        if p_id not in self.knows_about:
            warnings.warn("No info held on this character anyway")

        # populate list with all keys if knows about everything (filter on None)
        if self.knows_about[p_id] is None:
            self.knows_about[p_id] = Player(p_id).broadcastable

        print("Player " + self.p_id+ " is losing " + p_id + "from knows_about dict. Before:\n")
        print(self.knows_about.items())
        
        if lose_all:
            print("losing all info!")
            self.knows_about.pop(p_id)

        else:
            for attribute in attribute_filter:
                if attribute not in self.broadcastable:
                    raise ValueError("Attribute '"+attribute+"' is not a broadcastable attribute.")
                elif attribute in self.knows_about[p_id]:
                    self.knows_about[p_id].remove(attribute)
                else:
                    print("attribute: "+attribute+" was not found in player: "+self.p_id+"'s knows_about")

        print("After:\n")
        print(self.knows_about.items())

        self.save()

    # hard sets the information a player knows
    def set_info(self):
        raise NotImplementedError

    def leave_game(self, **kwargs):
        result = {}

        all_objects = muppy.get_objects()
        sum1 = summary.summarize(all_objects)
        summary.print_(sum1)

        if 'g_id' in kwargs:
            game = wwss.game.Game(kwargs['g_id'])
        elif 'g_id' in self.session:
            game = wwss.game.Game(self.session['g_id'])
        elif self.session.has_key("location") and self.session['location'] == "outgame":
            result['error'] = "Player not currently in a game."
            return result
        else:
            result['error'] = "Game not found"

        if self in game.players:
            game.remove_player(leaving_player=self)
            
            result['response'] = "Player removed from game"
        else:
            result['error'] = "Player not found in game: "+game.g_id
        
        if 'g_id' in self.session:
            self.session['location'] = "outgame"
            #self.session.pop('g_id', None)
            self.session.save()

        result['g_id'] = game.g_id

        return result

    def find_game(self, **kwargs):
        found_game = False
        if 'g_id' in self.session and 'location' in self.session and self.session['location'] == 'ingame':
            return {'text':"already ingame",
                    'g_id':self.session['g_id']}

        result = {}		# for debug purposes, output in lobby template http://localhost:8000/werewolves_game/lobby/
        result['text'] = ""
        result['error'] = ""

        # search method
        if 'g_id' in kwargs:
            g_list = ww_redis_db.keys("g_list:"+kwargs['g_id']+"*")
        elif 'g_name' in kwargs:
            # search for g_name in database TODO
            g_list = ww_redis_db.keys("g_list:*")
            result['text'] = "found game name in redis, joining"
        else:
            g_list = ww_redis_db.keys("g_list:*")		# should optimise by using SCAN http://redis.io/commands/scan, keys is warned as not for production
        
        if len(g_list) > 0:
            if 'g_name' in kwargs:
                for g_key in g_list:
                    if ww_redis_db.hget("name", g_key) == kwargs['g_name']:
                        found_game = True
                        g_id = str(g_key.decode("utf-8")).split(":")[1]
                        break
                if not found_game:
                    result['error'] = "Couldn't find game with that name."
            else:
                # find game with least spaces
                for g_key in g_list:
                    g_id = str(g_key.decode("utf-8")).split(":")[1]
                    game = wwss.game.Game(g_id)
                    if len(game.players) < 10:
                        game.add_player(joining_player=self)
                        
                        found_game = True
                        result['text'] = "found most space game"
                        break

        if not found_game:
            # start new game
            game = wwss.game.Game()
            game.name = "mynewgame"
            game.g_round = "1"
            game.add_player(joining_player=self)
            

            g_id = game.g_id
            result['text'] = "new game started"

        if 'computers' in kwargs:
            # populate with members
            result['text'] += ". Populated with AI."

        self.session['g_id'] = g_id
        self.session['location'] = "ingame"
        self.session.save()

        result['g_id'] = self.session['g_id']
        result['p_id'] = self.session['p_id']

        #import ipdb;ipdb.set_trace()

        return result
