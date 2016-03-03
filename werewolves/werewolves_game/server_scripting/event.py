import uuid
import warnings
import weakref
from collections import Counter
from random import shuffle

from swampdragon.pubsub_providers.data_publisher import publish_data

import werewolves_game.server_scripting as wwss
from werewolves_game.server_scripting.redis_util import *

# global callback handling/cancelling singleton
# class callback_handling:

# More events can be added here. Methods of characters can call this method to generate custom events.
class EventFactory():
	@classmethod
	def create_event(cls, e_type, game):
		if e_type == "night":
			return Event(game, game.get_group([wwss.characters.Werewolf, "alive"]), game.get_group([wwss.characters.Human, "alive"]), cls.lookup_action(e_type), e_type)
		if e_type == "day":
			return Event(game, game.get_group([wwss.characters.Character, "alive"]), game.get_group([wwss.characters.Character, "alive"]), cls.lookup_action(e_type), e_type)
		if e_type == "dying":
			return Event(game, game.get_group([wwss.characters.Witch, "alive"]), game.get_group(["dead", "last_event"]), cls.lookup_action(e_type), e_type)
		if e_type == "witch_save":
			raise NotImplementedError
			return Event(game, game.get_group([wwss.characters.Human]), game.get_group([wwss.characters.Witch]), cls.lookup_action(e_type), e_type)
		if e_type == "witch_kill":
			raise NotImplementedError
			return Event(game, game.get_group([wwss.characters.Character]), game.get_group([wwss.characters.Witch]), cls.lookup_action(e_type), e_type)

	@classmethod
	def event_from_redis(cls, game, instigators, subjects, e_type, result_subjects, e_id):
		return Event(game, instigators, subjects, cls.lookup_action(e_type), e_type, result_subjects, e_id)

	@classmethod
	def lookup_action(cls, e_type):
		if e_type == "night":
			return wwss.characters.Werewolf.attack
		if e_type == "day":
			return wwss.characters.Human.lynch
		if e_type == "dying":
			return wwss.characters.Witch.heal


# Handles broadcasting and vote hosting of the event
# Need to add some method of controlling information
class Event():
	def __init__(self, game, instigators, subjects, action, e_type, result_subjects=[], e_id=None):
		self.subjects = subjects			# list of those the events affects
		self.instigators = instigators		# list of those starting the event
		self.action = action				# function that will implement the effect
		self.game = game#weakref.ref(game)		# game always references this event, and can recreate from redis if required, meaning a dangling reference here can be garbage collected.
		self.e_type = e_type
		self.result_subjects = result_subjects
		self.votes = []
		self.callback_handler = []
		self.action_without_instigators = False

		if not e_id:		# not from redis
			e_id = str(uuid.uuid4())
			self.result_subjects = []

		self.e_id =  e_id
		return

	def __del__(self):
		self.save()

	def __eq__(self, other):
		return self.e_id == other.e_id

	def save(self):
		ww_redis_db.hset("event:"+self.e_id, "game", self.game.g_id)
		ww_redis_db.hset("event:"+self.e_id, "e_type", self.e_type)
		ww_redis_db.hset("event:"+self.e_id, "instigators", "|".join([player.p_id for player in self.instigators]))
		ww_redis_db.hset("event:"+self.e_id, "subjects", "|".join([player.p_id for player in self.subjects]))
		ww_redis_db.hset("event:"+self.e_id, "result_subjects", "|".join([player.p_id for player in self.result_subjects]))

	@classmethod
	def load(cls, game, e_id):
		redis_event = ww_redis_db.hgetall("event:"+e_id)
		redis_event = {k.decode('utf8'): v.decode('utf8') for k, v in redis_event.items()}

		instigators = subjects = result_subjects = []

		if redis_event["instigators"]:
			instigators = redis_event["instigators"].split("|")
		if redis_event["subjects"]:
			subjects = redis_event["subjects"].split("|")
		if redis_event["result_subjects"]:
			result_subjects = redis_event["result_subjects"].split("|")

		# creates new users based on p_id. Not v memory efficient. Check p_ids with game.players and see if you can reference them?
		instigators = [wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id) for p_id in instigators]
		subjects = [wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id) for p_id in subjects]
		result_subjects = [wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id) for p_id in result_subjects]

		return EventFactory.event_from_redis(game, instigators, subjects, redis_event["e_type"], result_subjects, e_id)

	def as_JSON(self):
		event_json = {}
		event_json['e_id'] = self.e_id
		event_json['e_type'] = self.e_type

		event_json['instigators'] = self.e_type
		event_json['subjects'] = self.e_type
		event_json['result_subjects'] = self.e_type

		instigators_json = {}
		for player in self.instigators:
			instigators_json[player.p_id] = player.as_JSON()	# causes duplication, but worth it?

		subjects_json = {}
		for player in self.subjects:
			subjects_json[player.p_id] = player.as_JSON()

		result_subjects_json = {}
		for player in self.result_subjects:
			result_subjects_json[player.p_id] = player.as_JSON()

		event_json['votes'] = self.votes

		# assuming event action can be inferred from e_type. Therefore not included in JSON.

		event_json['instigators'] = instigators_json
		event_json['subjects'] = self.subjects_json
		event_json['result_subjects'] = self.result_subjects_json

		return json.dumps(event_json, sort_keys=True, indent=4)

	def start(self):
		print("subjects of the event"+str(self.subjects))
		print("instigators of the event:"+str(self.instigators))
		if not self.subjects or not self.instigators:
			self.finish_event()
			return

		self.game.change_state("new_event")

		if len(self.subjects) > 1 or len(self.instigators) > 1:
			if len(self.subjects) != 1 and len(self.instigators) != 1:
				print("holding votes, multiple options available")
				self.hold_vote()
		
		if len(self.subjects) == 1:
			self.result_subjects = self.subjects
			print("only 1 option, starting it immediately")
			self.finish_event()

	def hold_vote(self):
		self.game.change_state("voting")

		self.callback_handler = self.game.iol.call_later(5, self.vote_result)

	def add_vote(self, p_id):
		# callrouter should do this
		print("Player just voted for: "+p_id)
		self.votes.append(p_id)
		if len(self.votes) == len(self.voters):
			self.game.change_state("finished_voting")
			self.game.iol.remove_timeout(self.callback_handler)

	def vote_result(self):
		if self.votes:
			p_id_most_common = Counter(self.votes).most_common(1)
			print("most common vote was:") 
			print(p_id_most_common)
			self.result_subjects = [self.game.get_group([p_id_most_common])]
		else:
			shuffle(self.subjects)
			print("No votes given, picking random:")
			print(self.subjects[0])
			self.result_subjects = [self.subjects[0]]

		self.game.change_state("finished_voting")
		self.finish_event()
		return

	def finish_event(self):
		print("result subjects of the event:"+str(self.result_subjects))
		if self.result_subjects and (self.instigators or self.action_without_instigators):		# only add to history if there is an effect
			self.game.event_history.append(self)

		self.game.event_queue.remove(self)
		
		for player in self.result_subjects:	# new events queued will be in reverse order to the order they were added to subjects
			result = self.action(player)
			if result and isinstance(result, Event):
				result = [result]
			if result and any(isinstance(e, Event) for e in result):
				[self.game.event_queue.insert(0, event) for event in result if isinstance(event, Event)]		# adds events with the same order they were returned

		if self.game.get_winners():
			self.game.change_state("game_finished")
		else:
			self.game.change_state("waiting")