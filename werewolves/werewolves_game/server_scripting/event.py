import uuid
import warnings
from collections import Counter

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
			raise NotImplementedError
			return Event(game, game.get_group([wwss.characters.Human, "alive"]), game.get_group([wwss.characters.Human, "alive"]), cls.lookup_action(e_type), e_type)
		if e_type == "dying":
			return Event(game, game.get_group(["dying"]), game.get_group([wwss.characters.Witch, "alive"]), cls.lookup_action(e_type), e_type)
		if e_type == "witch_save":
			raise NotImplementedError
			return Event(game, game.get_group([wwss.characters.Human]), game.get_group([wwss.characters.Witch]), cls.lookup_action(e_type), e_type)
		if e_type == "witch_kill":
			raise NotImplementedError
			return Event(game, game.get_group([wwss.characters.Character]), game.get_group([wwss.characters.Witch]), cls.lookup_action(e_type), e_type)

	@classmethod
	def event_from_redis(cls, game, instigators, subjects, e_type, votes, e_id):
		return Event(game, e_type, instigators, subjects, result_subjects, lookup_action(e_type), votes, e_id)

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
	def __init__(self, game, instigators, subjects, action, e_type, votes=[], e_id=None):
		self.subjects = subjects			# list of those the events affects
		self.instigators = instigators		# list of those starting the event
		self.action = action				# function that will implement the effect
		self.game = game
		self.e_type = e_type
		self.votes = votes

		if e_id:	# from redis
			self.result_subjects = self.vote_result()
		else:
			e_id = str(uuid.uuid4())
			self.result_subjects = []
			self.callback_handler = []

		self.e_id =  e_id

		print("subjects of the event"+str(subjects))
		print("instigators of the event:"+str(instigators))

		return

	def save(self):
		warnings.warn("splitting/joining of player values needs to be monitored for null values")
		ww_redis_db.hset("event:"+self.e_id, "game", self.game.g_id)
		ww_redis_db.hset("event:"+self.e_id, "e_type", self.e_type)
		ww_redis_db.hset("event:"+self.e_id, "instigators", "|".join([player.p_id for player in self.instigators]))
		ww_redis_db.hset("event:"+self.e_id, "subjects", "|".join([player.p_id for player in self.subjects]))
		ww_redis_db.hset("event:"+self.e_id, "votes", "|".join(self.votes))
		ww_redis_db.hset("event:"+self.e_id, "result_subjects", "|".join([player.p_id for player in self.result_subjects]))

	@classmethod
	def load(cls, game, e_id):
		redis_event = ww_redis_db.hgetall("event:"+self.e_id)
		redis_event = {k.decode('utf8'): v.decode('utf8') for k, v in redis_event.items()}

		instigators = redis_event["instigators"].split("|")
		subjects = redis_event["subjects"].split("|")
		votes = redis_event["votes"].split("")

		# creates new users based on p_id. Not v memory efficient. Check p_ids with game.players and see if you can reference them?
		instigators = [wwss.user.Player(p_id) for p_id in instigators]
		subjects = [wwss.user.Player(p_id) for p_id in subjects]

		return EventFactory.event_from_redis(game, instigators, subjects, redis_event["e_type"], votes, e_id)

	def start(self):
		self.game.change_state("new event")
		if len(self.subjects) > 1 and len(self.instigators) > 1:
			self.hold_vote()
		else:
			self.finish_event()

	def hold_vote(self):
		self.game.change_state("voting")
		data_dict = {}

		data_dict["subjects"] = []
		for player in self.subjects:
			data_dict["subjects"].append(player.as_JSON())

		data_dict["description"] = self.description
		data_dict["channel"] = "event info"

		for player in self.instigators:
			publish_data("player:"+player.p_id, data_dict)

		self.callback_handler = self.game.iol.call_later(10, self.vote_result)

	def add_vote(self, p_id):
		# callrouter does this
		self.votes.append(p_id)
		if len(self.votes) == len(self.voters):
			self.game.change_state("finished_voting")
			game.iol.remove_timeout(self.callback_handler)

	def vote_result(self):
		self.result_subjects = Counter(self.votes).most_common(1)
		self.game.change_state("finished_voting")
		
		print("most common vote was:")
		print(Counter(self.votes).most_common(1))
		return Counter(self.votes).most_common(1)

	def finish_event(self):
		for player in self.subjects:	# new events queued will be in reverse order to the order they were added to subjects
			result = self.action(player)
			if result and any(isinstance(e, Event) for e in result):
				[self.event_queue.insert(0, event) for event in result if isinstance(event, Event)]		# adds events with the same order they were returned

		self.game.event_history.append(self)
		self.game.event_queue.remove(self)

		if self.game.game_end():
			self.game.change_state("game finished")
		elif len(self.game.event_queue) > 0:
			self.game.event_queue[0].start()
		else:
			self.game.change_state("waiting")