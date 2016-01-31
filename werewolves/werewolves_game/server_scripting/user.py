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

	def __init__(self, p_id=None, session_key=None):
		self.name = ""
		self.g_history = []	# list of games just been in to assist matchmaking algorithm
		self.status = ""
		self.session_key = ""

		if session_key:
			self.session = SessionStore(session_key=session_key)
			self.session_key = session_key
			if 'p_id' in self.session:
				p_id = self.session['p_id']

		if p_id:
			self.p_id = p_id
			try:
				self.load(p_id)
			except Exception as error:
				print("couldn't load user's p_id from redis: "+str(error))
				print("putting in default values")

				self.name = "Richard"
				self.p_id = str(uuid.uuid4())
				self.status = "outgame"

				self.session['p_id'] = self.p_id
				self.session['status'] = self.status
				self.session.save()

				self.save()


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
		self.status = redis_player['status']
		self.g_history = (redis_player['g_history']).split("|")
		
		return True

	def save(self):
		ww_redis_db.hset("player_list:"+self.p_id, "session_key", self.session_key)
		ww_redis_db.hset("player_list:"+self.p_id, "name", self.name)		# save player to redis DB (see redis_util for more info)
		ww_redis_db.hset("player_list:"+self.p_id, "status", self.status)
		ww_redis_db.hset("player_list:"+self.p_id, "g_history", ("|").join(self.g_history))

	def as_JSON(self, user_json={}):
		user_json['p_id'] = self.p_id
		user_json['name'] = self.name
		return json.dumps(user_json, default=lambda o: o.__dict__, sort_keys=True, indent=4)

	def push_message(self, **kwargs):
		data_dict = {}
		channel = ""

		if 'msg' not in kwargs or 'groups' not in kwargs:
			return

		if (	'game' in kwargs['groups'] and
				'g_id' in self.session and
				'status' in self.session and
				self.session['status'] == "ingame"
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

	def __init__(self, p_id, session_key=None):
		if session_key:
			super().__init__(session_key=session_key)
		else:
			super().__init__(p_id=p_id)
		
		self.character = "unassigned"
		self.state = "alive"

	def load(self, p_id):
		redis_player = ww_redis_db.hgetall("player_list:"+str(p_id))
		redis_player = {k.decode('utf8'): v.decode('utf8') for k, v in redis_player.items()}

		if 'character' in redis_player:	# can be rewritten with all() keyword http://stackoverflow.com/questions/8041944/if-x-and-y-in-z
			self.character = redis_player['character']
		if 'state' in redis_player:
			self.state = redis_player['state']
		if 'g_id' in redis_player:
			self.g_id = redis_player['g_id']

		return super().load(p_id, redis_player)


	def save(self):
		super().save()
		ww_redis_db.hset("player_list:"+self.p_id, "state", self.state)
		ww_redis_db.hset("player_list:"+self.p_id, "character", self.character)
		ww_redis_db.hset("player_list:"+self.p_id, "g_id", self.g_id)

	def as_JSON(self, player_json={}):
		super().as_JSON(player_json)
		player_json['character'] = self.character
		player_json['state'] = self.state
		return json.dumps(player_json, default=lambda o: o.__dict__, sort_keys=True, indent=4)

	def leave_game(self, **kwargs):
		result = {}

		if 'g_id' in kwargs:
			game = werewolves_game.server_scripting.game.Game(kwargs['g_id'])
		elif 'g_id' in self.session:
			game = werewolves_game.server_scripting.game.Game(self.session['g_id'])
		elif self.session.has_key("status") and self.session['status'] == "outgame":
			result['error'] = "Player not currently in a game."
			return result
		else:
			result['error'] = "Game not found"

		if self in game.players:
			game.remove_player(self.p_id)
			
			result['response'] = "Player removed from game"
		else:
			result['error'] = "Player not found in game: "+game.g_id
		
		if 'g_id' in self.session:
			self.session['status'] = "outgame"
			#self.session.pop('g_id', None)
			self.session.save()

		result['g_id'] = game.g_id

		return result

	def find_game(self, **kwargs):
		found_game = False

		if 'g_id' in self.session and 'status' in self.session and self.session['status'] == 'ingame':
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
