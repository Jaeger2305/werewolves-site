import redis
import uuid
import json
from werewolves_game.server_scripting.redis_util import *
import werewolves_game.server_scripting.game
from tornado.ioloop import PeriodicCallback, IOLoop
from swampdragon.pubsub_providers.data_publisher import publish_data

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


class User:
	# user specific functions pertaining to general usage (login, cookies etc.)
	p_id = ""
	name = ""
	g_history = []	# list of games just been in to assist matchmaking algorithm
	session = None
	session_key = ""

	def __init__(self, key):
		self.session = SessionStore(session_key=key)
		self.session_key = key

		if 'p_id' in self.session.keys():
			self.load(self.session['p_id'])
		else:
			self.name = "Richard"
			self.p_id = str(uuid.uuid4())

			self.session['p_id'] = self.p_id
			self.session.save()

			self.save()

	def load(self, p_id, redis_player=None):
		self.p_id = p_id

		if not redis_player:
			redis_player = ww_redis_db.hgetall("player_list:"+str(p_id))
			redis_player = {k.decode('utf8'): v.decode('utf8') for k, v in redis_player.items()}

		if 'g_history' in redis_player.keys():
			self.g_history = (redis_player['g_history']).split("|")
		return

	def save(self):
		ww_redis_db.hset("player_list:"+self.p_id, "name", self.name)		# save player to redis DB (see redis_util for more info)
		ww_redis_db.hset("player_list:"+self.p_id, "g_history", ("|").join(self.g_history))

	def as_JSON(self, user_json={}):
		user_json['p_id'] = self.p_id
		user_json['name'] = self.name
		return json.dumps(user_json, default=lambda o: o.__dict__, sort_keys=True, indent=4)

	def push_message(self, **kwargs):
		data_dict = {}
		channel = ""

		if 'msg' not in kwargs.keys() or 'groups' not in kwargs.keys():
			return

		if (	'game' in kwargs['groups'] and
				'g_id' in self.session.keys() and
				'status' in self.session.keys() and
				self.session['status'] == "ingame"
			):
			channel = 'game:'+self.session['g_id']
		elif 'player' in kwargs['groups'] and 'p_id' in kwargs.keys():
			channel = 'player:'+kwargs['p_id']

		data_dict['message'] = kwargs['msg']
		data_dict['channel'] = channel

		publish_data(channel, data_dict)
		return data_dict

class Player(User):
	# game specific class for interacting with the game class (join, interact with other players generally)
	character = "unassigned"
	state = "alive"

	def __init__(self, key):
		super().__init__(key)

		if 'p_id' in self.session.keys():
			self.load(self.session['p_id'])
		else:
			self.character = "unassigned"
			self.state = "alive"

			self.save()

	def load(self, p_id):
		redis_player = ww_redis_db.hgetall("player_list:"+str(self.p_id))
		redis_player = {k.decode('utf8'): v.decode('utf8') for k, v in redis_player.items()}
		super().load(p_id, redis_player)

		if 'character' in redis_player.keys():
			self.character = redis_player['character']
		if 'state' in redis_player.keys():
			self.state = redis_player['state']

	def save(self):
		super().save()
		ww_redis_db.hset("player_list:"+self.p_id, "state", self.state)
		ww_redis_db.hset("player_list:"+self.p_id, "character", self.character)

	def as_JSON(self, player_json={}):
		super().as_JSON(player_json)
		player_json['character'] = self.character
		player_json['state'] = self.state
		return json.dumps(player_json, default=lambda o: o.__dict__, sort_keys=True, indent=4)

	def leave_game(self, **kwargs):
		result = {}

		if 'g_id' in kwargs.keys():
			game = werewolves_game.server_scripting.game.Game(kwargs['g_id'])
		elif 'g_id' in self.session.keys():
			game = werewolves_game.server_scripting.game.Game(self.session['g_id'])
		elif self.session['status'] == "outgame":
			result['error'] = "Player not currently in a game."
			return result
		else:
			result['error'] = "Game not found"

		if self.p_id in game.players:
			game.remove_player(self.p_id)
			
			result['response'] = "Player removed from game"
		else:
			result['error'] = "Player not found in game: "+game.g_id
		
		if 'g_id' in self.session.keys():
			self.session['status'] = "outgame"
			#self.session.pop('g_id', None)
			self.session.save()

		result['g_id'] = game.g_id

		return result

	def find_game(self, **kwargs):
		found_game = False

		if 'g_id' in self.session.keys() and 'status' in self.session.keys() and self.session['status'] == 'ingame':
			return {'text':"already ingame",
					'g_id':self.session['g_id']}

		result = {}		# for debug purposes, output in lobby template http://localhost:8000/werewolves_game/lobby/
		result['text'] = ""
		result['error'] = ""

		# search method
		if 'g_id' in kwargs.keys():
			g_list = ww_redis_db.keys("g_list:"+kwargs['g_id']+"*")
		elif 'g_name' in kwargs.keys():
			# search for g_name in database TODO
			g_list = ww_redis_db.keys("g_list:*")
			result['text'] = "found game name in redis, joining"
		else:
			g_list = ww_redis_db.keys("g_list:*")		# should optimise by using SCAN http://redis.io/commands/scan, keys is warned as not for production
		
		if len(g_list) > 0:
			if 'g_name' in kwargs.keys():
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
					game = werewolves_game.server_scripting.game.Game(g_id)
					if len(game.players) < 10:
						game.add_player(self.p_id)
						

						found_game = True
						result['text'] = "found most space game"
						break

		if not found_game:
			# start new game
			game = werewolves_game.server_scripting.game.Game()
			game.name = "mynewgame"
			game.g_round = "1"
			#newGame.players.append(self.p_id)
			game.add_player(self.p_id)
			

			g_id = game.g_id
			result['text'] = "new game started"

		if 'computers' in kwargs:
			# populate with members
			result['text'] += ". Populated with AI."

		self.session['g_id'] = g_id
		self.session['status'] = "ingame"
		self.session.save()

		result['g_id'] = self.session['g_id']
		result['p_id'] = self.session['p_id']

		return result
