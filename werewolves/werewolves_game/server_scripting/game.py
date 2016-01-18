''' header

	all functions and classes involving the python side of the application

	data is stored and accessed from redis
	instances of the classes are created from redis
	to modify the object data:
		myObj = Object(id)
		# do stuff...
		myObj.save()

	the individual functions are called from routers.py and either return information there, or broadcast it via PeriodicCallback()

	Most routers initialise a class found here and accesses it's functions

	Current class inheritance:

	event
	game
	user
		player
			character
				Werewolf_Witch_Mystic_etc
		Meta information (score, friends)

	Class for handling sessions? all the data that can be held in a session, makes it easy for us to manipulate
	And a debugging class that ties codes to messages?
	Messaging class?

	Variables should be privatised!!
'''
# If last player in game (ie players = 0), delete game from redis too

import redis
import uuid
from werewolves_game.server_scripting.redis_util import *

from tornado.ioloop import PeriodicCallback
from swampdragon.pubsub_providers.data_publisher import publish_data

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

class User:
	# user specific functions pertaining to general usage (login, cookies etc.)
	p_id = ""

class Character:
	# character specific class interacting with events
	allegiance = ""

class Werewolf_Witch_Mystic_etc:
	# special characters
	abilities = ""

class Player:
	# game specific class for interacting with the game class (join, interact with other players generally)
	# inherits from User
	p_id = ""
	character_type = ""
	status = ""
	name = ""
	session = None
	session_key = ""
	g_id = ""

	def __init__(self, key):
		self.session = SessionStore(session_key=key)
		self.session_key = key

		if 'p_id' in self.session.keys():
			self.load(self.session['p_id'])
		else:
			self.character_type = "werewolf"
			self.status = "alive"
			self.name = "Richard"
			self.p_id = str(uuid.uuid4())

			#import ipdb;ipdb.set_trace()
			self.session['p_id'] = self.p_id
			self.session.save()

			self.save()

	def load(self, p_id):
		redis_player = ww_redis_db.hgetall("player_list:"+str(p_id))
		redis_player = {k.decode('utf8'): v.decode('utf8') for k, v in redis_player.items()}

		self.p_id = p_id
		#self.name = redis_player['name']
		return

	def save(self):
		ww_redis_db.hset("player_list:"+self.p_id, "name", self.name)		# save player to redis DB (see redis_util for more info)

	def leave_game(self, **kwargs):
		result = {}

		if 'g_id' in kwargs.keys():
			game = Game(kwargs['g_id'])
		elif 'g_id' in self.session.keys():
			game = Game(self.session['g_id'])
		elif self.session['status'] == "outgame":
			result['error'] = "Player not currently in a game."
			return result
		else:
			result['error'] = "Game not found"

		if 'player:'+self.p_id in game.players:
			game.players.remove('player:'+self.p_id)
			game.save()
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
					game = Game(g_id)
					if len(game.players) < 10:
						game.add_player(self.p_id)
						game.save()

						found_game = True
						result['text'] = "found most space game"
						break

		if not found_game:
			# start new game
			game = Game()
			game.name = "mynewgame"
			game.g_round = "1"
			#newGame.players.append("player:"+self.p_id)
			game.players = ["player:"+self.p_id]
			game.save()

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

class Game:
	g_id = ""
	name = "Richard's room"
	g_round = 0
	players = []
	state = ""
	saved = False

	options = {
		'max_players': 2,
	}

	def __init__(self, g_id=None, session_key=None):
		if g_id is None and session_key is not None:
			session_data = SessionStore(session_key=session_key)
			if 'g_id' in session_data.keys():
				g_id = session_data['g_id']

		if not self.load(g_id):
			self.g_id = str(uuid.uuid4())
			self.state = "lobby"
			self.g_round = 0

	def save(self):
		ww_redis_db.hset("g_list:"+self.g_id, "name", self.name)
		ww_redis_db.hset("g_list:"+self.g_id, "round", self.g_round)
		ww_redis_db.hset("g_list:"+self.g_id, "state", self.state)
		players_string = ""
		if len(self.players) > 0:
			players_string = "|".join(self.players)

		ww_redis_db.hset("g_list:"+self.g_id, "players", players_string)

	def load(self, g_id):
		if g_id is None:
			return False

		redis_game = ww_redis_db.hgetall("g_list:"+str(g_id))
		redis_game = {k.decode('utf8'): v.decode('utf8') for k, v in redis_game.items()}

		if not redis_game:
			return False

		self.g_id = g_id
		self.players = redis_game['players'].split('|')
		self.state = redis_game['state']

		return True

	def delete(self):
		ww_redis_db.delete("g_list:"+self.g_id)

	def is_saved(self):
		if self.saved:
			return True
		else:
			return False

	def get_players(self):
		return self.players

	def get_g_round(self):
		return self.g_round

	def set_g_round(self, round_number):
		self.g_round = round_number

	def state_change(self, state):
		data_dict = {}
		data_dict['state'] = state
		data_dict['channel'] = "game:"+self.g_id

		publish_data("game:"+self.g_id, data_dict)

	def add_player(self, p_id):
		if "player:"+p_id not in self.players:
			self.players.append("player:"+p_id)

		if len(self.players) == self.options['max_players']:
			self.state_change("ready")

	def remove_player(self, p_id):
		while "player:"+p_id in self.players:
			self.players.remove("player:"+p_id)

class Event:
	def __init__():
		return



# should use tasks scheduler programs for this (ie Celery), not global functions, but fine for development
pcb = None

def broadcast_games():
	global pcb
	data_dict = {}
	games_dict = {}

	if pcb is None:
		pcb = PeriodicCallback(broadcast_games, 5000)
		pcb.start()

	g_list = ww_redis_db.keys("g_list:*")
	for v in g_list:
		v = v.decode("utf-8")

		if len(g_list) > 0:
			# find game with least spaces
			for g_key in g_list:
				g_id = str(g_key.decode("utf-8")).split(":")[1]
				game = Game(g_id)

				games_dict[g_key.decode("utf-8")] = str(len(game.players))

	data_dict["games"] = games_dict
	data_dict["channel"] = "lobbyinfo"

	publish_data("lobbyinfo", data_dict)
	return data_dict

def push_system_message(msg):
	data_dict = {}
	data_dict["message"] = msg

	data_dict["channel"] = "sysmsg"

	publish_data("sysmsg", data_dict)
	return data_dict

pcb2 = None
cur_g_id = None

# redundant and is broken
def broadcast_players(g_id):
	global pcb2
	global cur_g_id
	data_dict = {}

	if pcb2 is None:
		cur_g_id = g_id
		pcb2 = PeriodicCallback(lambda: broadcast_players(g_id), 4000)
		pcb2.start()
	elif cur_g_id != g_id:
		cur_g_id = g_id
		pcb2.stop()
		pcb2 = PeriodicCallback(lambda: broadcast_players(g_id), 4000)
		pcb2.start()

	g_list = ww_redis_db.keys(g_id+"*")
	for v in g_list:
		v = v.decode("utf-8")

		if len(g_list) > 0:
			# find game with least spaces
			for g_key in g_list:
				game = ww_redis_db.hgetall(g_key)
				game = {k.decode('utf8'): v.decode('utf8') for k, v in game.items()}	#convert from byte array to string dict

				players = game['players'].split("|")		# obtain players in current game in the form of player:uuid

				data_dict[g_key.decode("utf-8")] = str(len(players))

	data_dict["channel"] = "player_list"

	publish_data("player_list:"+g_id, data_dict)

	return data_dict

from django.contrib.sessions.models import Session

pcb3 = None
def check_activity():
	global pcb3

	if pcb3 is None:
		pcb3 = PeriodicCallback(lambda: check_activity(), 10000)
		pcb3.start()

	sessions = Session.objects.all()

	for s in sessions:
		print(s.get_decoded())

	return
