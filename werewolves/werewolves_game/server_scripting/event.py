from collections import Counter
from werewolves_game.server_scripting.characters import Werewolf, Witch, Human
import uuid

# global callback handling/cancelling singleton
# class callback_handling:

# More events can be added here. Methods of characters can call this method to generate custom events.
class EventFactory():
	@classmethod
	def create_event(cls, event, game):
		if event == "night":
			return Event(game, game.get_group(Werewolf), game.get_group(Human), Werewolf.attack, "Werewolves attacking")
		if event == "day":
			return Event(game, game.get_group(Human), game.get_group(Human), Human.lynch, "Lynch mob time")
		if event == "witch_save":
			raise NotImplementedError
			return Event(game, game.get_group(Human), game.get_group(Witch), Witch.save_player, "Save this player?")
		if event == "witch_kill":
			raise NotImplementedError
			return Event(game, game.get_group(Character), game.get_group(Witch), Witch.kill_player, "Kill this player?")

# Handles broadcasting and vote hosting of the event
# Need to add some method of controlling information
class Event():
	def __init__(self, game, subjects, instigators, action, description):
		self.subjects = subjects			# list of those the events affects
		self.instigators = instigators		# list of those starting the event
		self.action = action				# function that will implement the effect
		self.game = game
		self.description = description

		self.e_id = uuid.uuid4()
		self.votes = []
		self.result_subjects = []
		self.callback_handler = []

		print("subjects of the event"+str(subjects))
		print("instigators of the event:"+str(instigators))

		return

	def start(self):
		self.game.change_state("new event")
		if len(self.subjects) > 1 and len(self.instigators) > 1:
			self.hold_vote()
		else:
			self.finish_event()

	def hold_vote():
		self.game.change_state("voting")
		data_dict = {}

		data_dict["subjects"] = []
		for player in self.subjects:
			data_dict["subjects"].append(player.as_JSON())

		data_dict["description"] = self.description
		data_dict["channel"] = "event info"

		for player in self.instigators:
			publish_data("player:"+player.p_id, data_dict)

		self.callback_handler = game.iol.call_later(10, self.vote_result)

	def add_vote(self, p_id):
		# callrouter does this
		self.votes.append(p_id)
		if len(self.answers) == len(self.voters):
			self.game.change_state("finished_voting")
			game.iol.remove_timeout(self.callback_handler)

	def vote_result(self):
		self.result_subjects = Counter(self.answers).most_common(1)
		self.game.change_state("finished_voting")
		
		print("most common vote was:")
		print(Counter(self.answers).most_common(1))
		return Counter(self.answers).most_common(1)

	def finish_event(self):
		for player in self.subjects:
			result = self.action(player)
			if isinstance(result, Event):
				self.event_queue.insert(0,result)

		self.game.event_history.append(self)
		self.game.event_queue.remove(self)

		if self.game.game_end():
			self.game.change_state("game finished")
		elif len(self.game.event_queue) > 0:
			self.game.event_queue[0].start()
		else:
			self.game.change_state("waiting")