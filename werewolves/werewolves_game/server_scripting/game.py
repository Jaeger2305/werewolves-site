''' game.py - handles Game()

	game.state = ['voting', 'lobby', 'discussion', 'starting']

	Event
	Game
	User
		Player
			Character
				Werewolf, Human, Witch, Mystic_etc
		Meta information (score, friends)
'''
import warnings
import redis
import uuid
import json
import inspect
from random import shuffle
from math import ceil

from werewolves_game.server_scripting.redis_util import *		# for the ww_redis_handler. Redundant for that purpose, it should be found in the swampdragon file redis_publisher
import werewolves_game.server_scripting.user as user
from werewolves_game.server_scripting.characters import Human, Werewolf, Witch, Character, CharacterFactory
import werewolves_game.server_scripting as wwss
import werewolves_game.server_scripting.event as event

from tornado.ioloop import PeriodicCallback, IOLoop
from swampdragon.pubsub_providers.data_publisher import publish_data

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

# create an object pool to draw from https://gist.github.com/pazdera/1124839
class GamePool:
	pass

class Game:
	@classmethod
	def check_exists(cls, g_id):
		# check GamePool Singleton to see if this game already exists, otherwise recycle an object if pool is full, or create new
		raise NotImplementedError


	def __init__(self, g_id=None, session_key=None, name="myRoom", options=None):
		self.options = {	'max_players': 4,
							'mystic': False,
							'witch': False	}
		
		self.players = []	# list of Players
		self.event_queue = []	# events waiting to happen. Triggered based on Game.state
		self.event_history = []	# past events

		if g_id is None and session_key is not None:
			session_data = SessionStore(session_key=session_key)
			if 'g_id' in session_data:
				g_id = session_data['g_id']

		try:
			self.load(g_id)
		except Exception as error:
			print(error)
			print("Creating default game values")
			self.g_id = str(uuid.uuid4())
			self.g_round = 0
			self.name = name
			self.state = "matchmaking"	# default. Currently unused

		self.saved = False		# enables chain editing
		self.iol = IOLoop.current()	# main tornado loop uses for callbacks

	def __del__(self):
		if not self.is_saved():
			self.save()
		self.characters = {}
		self.players = []

	def __eq__(self, other):
		return self.g_id == other.g_id

	def save(self):
		ww_redis_db.hset("g_list:"+self.g_id, "name", self.name)
		ww_redis_db.hset("g_list:"+self.g_id, "g_round", self.g_round)
		ww_redis_db.hset("g_list:"+self.g_id, "state", self.state)
		
		players_string = cur_events_string = old_events_string = ""
		if self.players:
			players_string = "|".join(self.get_player_ids())
		ww_redis_db.hset("g_list:"+self.g_id, "players", players_string)
		
		if self.event_queue:
			cur_events_string = "|".join([event.e_id for event in self.event_queue])
		ww_redis_db.hset("g_list:"+self.g_id, "event_queue", cur_events_string)
		
		if self.event_history:
			old_events_string = "|".join([event.e_id for event in self.event_history])
		ww_redis_db.hset("g_list:"+self.g_id, "event_history", old_events_string)

		for event in self.event_queue:
			event.save()

		for event in self.event_history:
			event.save()

		for player in self.players:
			player.save()

		games_dict = {}
		data_dict = {}
		games_dict["json"] = self.as_JSON()

		data_dict["game"] = games_dict
		data_dict["channel"] = "game:"+self.g_id

		publish_data("game:"+self.g_id, data_dict)

		self.saved = True

	def load(self, g_id):
		if g_id is None:
			raise Exception("No g_id supplied")

		redis_game = ww_redis_db.hgetall("g_list:"+str(g_id))
		redis_game = {k.decode('utf8'): v.decode('utf8') for k, v in redis_game.items()}

		if not redis_game:
			raise Exception("g_list:"+str(g_id)+" was not found in redis")

		self.g_id = g_id
		self.name = redis_game['name']
		self.g_round = int(redis_game['g_round'])

		# static method of redis_class split a "|" separated string and return initialised versions of each id
		# needs refactoring somehow

		if redis_game['players']:
			player_ids = redis_game['players'].split('|')
			for p_id in player_ids:
				if p_id not in self.get_player_ids():
					player = user.Player(p_id)
					self.players.append(CharacterFactory.create_character(player.character, p_id=player.p_id))
		else:
			self.players = []

		if redis_game['event_history']:
			event_ids = redis_game['event_history'].split("|")
			for e_id in event_ids:
				if e_id not in [event.e_id for event in self.event_history]:
					self.event_history.append(event.Event.load(self, e_id))

		if redis_game['event_queue']:
			event_ids = redis_game['event_queue'].split("|")
			for e_id in event_ids:
				if e_id not in [event.e_id for event in self.event_queue]:
					self.event_queue.append(event.Event.load(self, e_id))

		self.state = redis_game['state']

		return True

	def as_JSON(self, meta=True, players=False, cur_events=False, hist_events=False):
		game_obj = {}

		# default information
		game_obj['state'] = self.state

		if meta:
			game_obj['g_id'] = self.g_id
			game_obj['name'] = self.name
			game_obj['g_round'] = self.g_round


		# if asked for
		if players:
			players_json = {}
			for player in self.players:
				players_json[player.p_id] = player.as_JSON()

			game_obj['players'] = players_json

		if cur_events:
			event_history_json = {}
			for event in self.event_history:
				event_history_json[event.e_id] = event.as_JSON()

			game_obj['event_queue'] = event_queue_json

		if hist_events:
			event_queue_json = {}
			for event in self.event_queue:
				event_queue_json[event.e_id] = event.as_JSON()

			game_obj['event_history'] = event_history_json


		return json.dumps(game_obj, sort_keys=True, indent=4)

	# filters the players out of the json array dependent on a players knows_about dict
	def filter_JSON(self, game_json, filters):
		#import ipdb;ipdb.set_trace()
		players_json = {}

		knows_about = self.get_group(filters.keys())

		for player in knows_about:
			if player.p_id in filters:
				players_json[player.p_id] = player.as_JSON(attribute_filter=filters[player.p_id])
			else:
				print("You were probably expecting a different p_id. Check the User() init function!")


		game_obj = json.loads(game_json)
		game_obj['players'] = players_json
		game_json = json.dumps(game_obj, sort_keys=True, indent=4)

		return game_json

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

	def get_player_ids(self):
		return [player.p_id for player in self.players]

	def get_group(self, selectors):
		# loop through self.players and remove those that don't fit the group as an array
		group_list = self.players

		for selector in selectors:
			# selecting based on player.state
			if selector in ("alive", "dead", "dying"):
				group_list = [player for player in group_list if player.state == selector]

			# selecting based on last event
			elif selector == "last_event":
				group_list = [player for player in group_list if player in self.event_history[0].result_subjects]

			# selecting based on Class type
			elif inspect.isclass(selector) and issubclass(selector, Character):
				group_list = [player for player in group_list if isinstance(player, selector)]

			# selecting based on uuid string
			elif isinstance(selector, str):
				if uuid.UUID(selector, version=4):
					group_list = [player for player in group_list if player.p_id in self.get_player_ids()]
					print("found p_id in game, returning player object")

		return group_list

	def assign_roles(self):
		shuffle(self.players)
		werewolves_count = ceil(0.3*self.options['max_players'])

		if self.options['witch']:
			witch_count = ceil(0.1*self.options['max_players'])
		else:
			witch_count = 0

		for x in range(werewolves_count):
			self.players[x].character = "werewolf"

		for x in range(werewolves_count, werewolves_count+witch_count):
			self.players[x].character = "witch"

		for x in range(werewolves_count+witch_count, len(self.players)):
			self.players[x].character = "human"

		for i, player in enumerate(self.players):
			self.players[i] = CharacterFactory.create_character(player.character, p_id=player.p_id)
			self.players[i].game = self	# raises errors if actions done on characters not through the game
			self.players[i].save()
			print(player.character)

	def start_game(self):
		print("game starting")
		self.assign_roles()
		self.change_state("waiting")

		print("First round: night dawns.")
		
		self.g_round += 1

		newEvent = event.EventFactory.create_event("night", self)

		self.event_queue.append(newEvent)	# should always be event_queue[0] if from scratch (problems if loaded from redis?)

		self.check_event_queue()

	def end_game(self):
		raise NotImplementedError

	# publishes data to channels based on current state
	# needs to be complemented by a filter function
	def change_state(self, state):
		self.state = state
		data_dict = {}

		if state == "lobby":
			print("waiting for more players")

		if state == "ready":
			print("publishing ready info")

		if state == "waiting":
			print("waiting for event")

		if state == "new_event":
			print("new event starting: " + self.event_queue[0].e_type)
			data_dict["event"] = self.event_queue[0].e_type

		if state == "voting":
			print("Waiting 10s to collect votes")

			cur_event = self.event_queue[0]

			data_dict["subjects"] = []
			for player in cur_event.subjects:
				data_dict["subjects"].append(player.as_JSON())

			data_dict["e_type"] = cur_event.e_type
			data_dict["channel"] = "event info"

			for player in cur_event.instigators:
				publish_data("player:"+player.p_id, data_dict)

		if state == "finished_voting":
			print("Votes collected, performing result")

		if state == "game_finished":
			#save to DB, kick all players etc.
			winners = "These guys won: "
			for group in self.get_winners():
				winners = winners+group+", "

			print("-------"+winners.upper()+"-------")


		self.save()

	def check_event_queue(self):
		if self.state == "game_finished":
			self.end_game()												# tidy up
			return

		if not self.event_queue:										# add new event based on round
			print("No event in queue, adding day/night")

			self.g_round += 1

			if self.g_round % 2:
				e_type = "night"
			else:
				e_type = "day"

			newEvent = event.EventFactory.create_event(e_type, self)
			self.event_queue.append(newEvent)
			self.change_state("new_event")
		
		if self.state == "new_event" or self.state == "waiting":				# work through queue
			print("event in the queue, we've been waiting to start")
			self.event_queue[0].start()
		else:
			print("event in progress, resetting callback but nothing changed")

		self.iol.call_later(10, self.check_event_queue)					# permits constant callback. BUG: never cleaned up as I'm not saving the handler to remove from iol.

	def get_winners(self):
		winners = ["humans", "werewolves"]

		if self.get_group([Human, "alive"]):
			winners.remove("werewolves")

		if self.get_group([Werewolf, "alive"]):
			winners.remove("humans")

		return winners

	def add_player(self, p_id=None, joining_player=None):
		import ipdb;ipdb.set_trace()
		if p_id:
			joining_player = user.Player(p_id)
		if joining_player not in self.players:
			# add a weakref to game
			joining_player.game_instance = self	# this is rather hidden and unused. Delete?
			self.players.append(joining_player)

			# share around the information
			for ingame_player in self.players:
				if joining_player != ingame_player:
					# give ingame player information about joining player
					ingame_player.gain_info(['p_id', 'name'], info_player=joining_player)

					# give joining player information about ingame_players
					joining_player.gain_info(['p_id', 'name'], info_player=ingame_player)

		if len(self.players) >= self.options['max_players']:
			print("Game full, starting now")
			self.change_state("ready")
			self.start_game()
			#self.iol.call_later(3, self.change_state, "ready")

		self.save()

	def remove_player(self, p_id=None, leaving_player=None):
		if p_id:
			leaving_player = self.get_group([p_id])

		for ingame_player in self.players:
			if leaving_player != ingame_player:
				leaving_player.lose_info(None, info_player=ingame_player, lose_all=True)
				ingame_player.lose_info(None, info_player=leaving_player, lose_all=True)

		while leaving_player in self.players:
			self.players.remove(leaving_player)
		
		self.save()



# should use tasks scheduler programs for this (ie Celery), not global functions, but fine for development
pcb = None

def broadcast_games():
	global pcb
	data_dict = {}
	games_dict = {}

	if pcb is None:
		pcb = PeriodicCallback(broadcast_games, 6000)
		pcb.start()

	g_list = ww_redis_db.keys("g_list:*")
	for v in g_list:
		v = v.decode("utf-8")

		if len(g_list) > 0:
			# find game with least spaces
			for g_key in g_list:
				g_id = str(g_key.decode("utf-8")).split(":")[1]
				game = Game(g_id)
				
				games_dict["game:"+g_id] = game.as_JSON()

	data_dict["game"] = games_dict
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
