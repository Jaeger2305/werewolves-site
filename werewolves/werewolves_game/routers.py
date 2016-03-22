from django.contrib.sessions.models import Session # redundant? Temp using it in session_handling
from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

from swampdragon import route_handler
from swampdragon.route_handler import ModelPubRouter, BaseRouter

from werewolves_game.server_scripting.game import *     # bad practice
from werewolves_game.server_scripting.user import Player, User
from werewolves_game.server_scripting.redis_util import *

class GameRouter(BaseRouter):
    route_name = 'game'
    valid_verbs = BaseRouter.valid_verbs + []

class LobbyRouter(BaseRouter):
    route_name = 'lobby'
    valid_verbs = BaseRouter.valid_verbs + ['broadcast_games', 'messaging', 'session_handling', 'init', 'matchmaking', 'vote', 'developer']

    # all published methods pass through this func, the returned array of strings are the channels the messages are broadcast on.
    # defaults to first element (lobbyinfo)
    def get_subscription_channels(self, **kwargs):
        channels = ['lobbyinfo', 'playersInGame', 'sysmsg']
        
        # subscribing
        if 'session_key' in kwargs and kwargs['session_key'] is not None:
            session = SessionStore(session_key=kwargs['session_key'])
            if 'g_id' in session:
                channels.append('game:'+session['g_id'])
            if 'p_id' in session:
                channels.append('player:'+session['p_id'])

        # redundant?
        if 'output' in kwargs:
            if kwargs['output'] == 'player_list':
                return ['player_list:'+kwargs['g_id']]
            elif kwargs['output'].startswith("game:"):
                return ['game:'+kwargs['g_id']]

        # unsubscribing
        if ('action' in kwargs and kwargs['action'] == "unsubscribe"
            and 'listener' in kwargs and kwargs['listener'] == "game"
            ):
            unsub_channels = []
            for channel in channels:
                if channel.startswith(kwargs['listener']):
                    unsub_channels.append(channel)

            return unsub_channels

        return channels

    def init(self, **kwargs):
        if "session_key" in kwargs:
            initUser = User(session_key=str(kwargs['session_key']))     # this ensures the user's session is stored with the p_id in redis, allowing subsequent calls to redis to require only the p_id
            self.send("initialised user into Redis")
        else:
            return self.send({"error":"no session key supplied"})

    def developer(self, **kwargs):
        if kwargs['action'] == "test_game":
            for x in range(1,int(kwargs['player_count'])):
                player = Player(session_key=User(session_key=x).session_key)
                player.find_game()

            myPlayer = Player(session_key=kwargs['session_key'])
            myPlayer.find_game()

        elif kwargs['action'] == "ask_update":
            import ipdb;ipdb.set_trace()
            myPlayer = Player(session_key=kwargs['session_key'])
            myGame = Game(session_key=kwargs['session_key'])

            full_json = myGame.as_JSON()
            filtered_json = myGame.filter_JSON(full_json, myPlayer.knows_about)

            self.send(filtered_json)


    def session_handling(self, **kwargs):
        if 'action' not in kwargs:
            return self.send({"error":"no action given"})

        if kwargs['action'] == "delete":
            Session.objects.all().delete()
            return
        elif kwargs['action'] == "check":
            check_activity()
            return

    def matchmaking(self, **kwargs):
        if 'action' not in kwargs:
            return self.send({"error":"no action given"})

        session_data = SessionStore(session_key=kwargs['session_key'])

        if kwargs['action'] == "flush_db":
            ww_redis_db.flushall()     # use to clear redis of all keys to start afresh
            session_data.flush()
            self.send("flushed!")
            return

        if "p_id" in session_data:
            player = Player(session_data['p_id'])
        else:
            print("error: p_id not been assigned to session")
            raise TypeError

        if kwargs['action'] == "join_game":
            response = player.find_game(**kwargs)
        elif kwargs['action'] == "leave_game":
            response = player.leave_game(**kwargs)


        self.send(response)

    def messaging(self,**kwargs):
        # requires target, session
        if "session_key" not in kwargs:
            self.send("error: no sesh")
            return
        if "target" not in kwargs:
            self.send("no target given")
            return

        session_data = SessionStore(session_key=kwargs['session_key'])

        sender = session_data['p_id']

        if kwargs['target'] == "player":
            if "id" in kwargs:
                user = user(kwargs['id'])
                user.give_message(kwargs['msg'], sender, kwargs['target'], kwargs['time'])
            else:
                self.send("please give ID of the player")
                return
        elif kwargs['target'] == "game":
            #import ipdb;ipdb.set_trace()
            game = Game(session_data['g_id'])

            for user in game.players:
                user.give_message(kwargs['msg'], sender, kwargs['target'], kwargs['time'])

        elif kwargs['target'] == "world":
            data_dict = {}

            data_dict['message'] = kwargs['msg']
            data_dict['sender'] = sender
            data_dict['target'] = kwargs['target']
            data_dict['time'] = kwargs['time']
            data_dict['type'] = "message"
            data_dict['channel'] = "sysmsg"
            channel = "sysmsg"

            publish_data(channel, data_dict)
        #else:  # search through game given this grouping (witch, werewolf, humans etc.)

    def vote(self, **kwargs):
        myGame = Game(session_data['g_id'])
        myGame.event_queue[0].add_vote(kwargs['p_id'])
        raise NotImplementedError

    def broadcast_games(self, *kwargs):
        return self.send(broadcast_games())

# register router
route_handler.register(LobbyRouter)
route_handler.register(GameRouter)