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

	component out the messaging system from player? http://gameprogrammingpatterns.com/component.html
	create a factory for the game
'''
# If last player in game (ie players = 0), delete game from redis too

import redis
import uuid
import json
from werewolves_game.server_scripting.redis_util import *		# for the ww_redis_handler. Redudundant for that purpose, it should be found in the swampdragon file redis_publisher
import werewolves_game.server_scripting.user as user
from werewolves_game.server_scripting.characters import Character, Werewolf, Witch

from tornado.ioloop import PeriodicCallback, IOLoop
from swampdragon.pubsub_providers.data_publisher import publish_data

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
from django.contrib.sessions.models import SessionStore		# redundant to have both?

from random import shuffle
from math import ceil

class GameManager:
	def __init__(self):
		return

	# allocate a player to a game

class Game:
	g_id = ""
	name = "Richard's room"
	g_round = 0
	players = []	# list of Players
	characters = {}
	state = ""
	saved = False		# async issues?
	iol = {}	# main tornado loop uses for callbacks
	history = []	# list of Events
	callback_queue = {}

	# should be populated based on redis/create game function call
	options = {	'max_players': 2,
				'fortune_teller': False,
				'witch': False	}

	def __init__(self, g_id=None, session_key=None):
		if g_id is None and session_key is not None:
			session_data = SessionStore(session_key=session_key)
			if 'g_id' in session_data.keys():
				g_id = session_data['g_id']

		if not self.load(g_id):
			self.g_id = str(uuid.uuid4())
			self.state = "lobby"
			self.g_round = 0

		self.iol = IOLoop.current()

	def __del__(self):
		self.characters = {}


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
		if redis_game['players'] != "":
			self.players = redis_game['players'].split('|')
		else:
			self.players = []

		self.state = redis_game['state']

		return True

	def as_JSON(self):
		json.dumps(self)

	def delete(self):
		ww_redis_db.delete("g_list:"+self.g_id)

	# in here in case I want to chain together multiple operations, avoiding multiple DB calls. More faff than it's worth?
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

	def assign_roles(self):
		shuffle(self.players)
		self.characters = []
		werewolves_count = ceil(0.3*self.options['max_players'])
		witch_count = 0

		for x in range(werewolves_count):
			self.characters.append(Werewolf(self.players[x]))
			#self.characters[self.players[x]] = "werewolf"

		if self.options['witch']:
			witch_count = ceil(0.1*self.options['max_players'])
			for x in range(werewolves_count, witch_count):
				self.characters.append(Witch(self.players[x]))
				#self.characters[self.players[x]] = "witch"

		for x in range(werewolves_count+witch_count, len(self.players)):
			self.characters.append(Character(self.players[x]))
			#self.characters[self.players[x]] = "human"

		for x in range(len(self.players)):
			# save to redis
			player = user.Player(self.players[x])
			player.character = "werewolf"#self.characters[self.players[x]]
			player.save()

		print(self.characters)

	def state_change(self, state):
		if state == "ready":
			self.assign_roles()

		data_dict = {}
		data_dict['state'] = state
		data_dict['channel'] = "game:"+self.g_id

		publish_data("game:"+self.g_id, data_dict)

	def add_player(self, p_id):
		if p_id not in self.players:
			self.players.append(p_id)

		if len(self.players) == self.options['max_players']:
			start_handler = self.iol.call_later(2, self.state_change, "ready")
			self.callback_queue["start_handler"] = start_handler
			#self.state_change("ready")

		self.save()

	def remove_player(self, p_id):
		while p_id in self.players:
			self.players.remove(p_id)

		self.save()



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

				games_dict[g_id] = str(len(game.players))
				#games_dict["json"] = game.as_JSON()

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

				players = game['players'].split("|")		# obtain players in current game in the form of uuid

				data_dict[g_key.decode("utf-8")] = str(len(players))

	data_dict["channel"] = "player_list"

	publish_data("player_list:"+g_id, data_dict)

	return data_dict



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
