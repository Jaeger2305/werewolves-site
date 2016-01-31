from werewolves_game.server_scripting.user import Player

# causes reinitialisation right up to the User
# alternatively, changing .__class__ is possible. But sounds pretty bad practice. http://stackoverflow.com/questions/13280680/how-dangerous-is-setting-self-class-to-something-else
class CharacterFactory:
	@classmethod
	def create_character(cls, character, **kwargs):
		if character == "unassigned":
			return Character(**kwargs)
		if character == "werewolf":
			return Werewolf(**kwargs)
		if character == "witch":
			return Witch(*args)
		if character == "human":
			return Human(**kwargs)

class Character(Player):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

class Human(Character):
	@classmethod
	def lynch(cls, character):
		return character.lynched()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.character = "human"

	def attacked_by_werewolves(self):
		print(self.p_id+" attacked by werewolves!")
		return EventFactory.create_event()


class Witch(Human):
	# character specific class interacting with events

	def __init__(self, **kwargs):
		super().__init(**kwargs)
		self.character = "witch"


class Werewolf(Human):
	@classmethod
	def attack(cls, character):
		return character.attacked_by_werewolves()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.character = "werewolf"