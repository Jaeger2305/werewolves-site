import warnings

from werewolves_game.server_scripting.user import Player
import werewolves_game.server_scripting.event as event

# causes reinitialisation right up to the User
# alternatively, changing .__class__ is possible. But sounds pretty bad practice. http://stackoverflow.com/questions/13280680/how-dangerous-is-setting-self-class-to-something-else
class CharacterFactory:
	@classmethod
	def create_character(cls, character, **kwargs):
		if character is None and p_id in kwargs:
			myPlayer = Player(kwargs['p_id'])
			character = myPlayer.character

		if character == "unassigned":
			warnings.warn("Character created with no role. Should not be initialised until player.character has been assigned via game.assign_roles(). Could lead to undefined behaviour if used ingame.")
			return Character(**kwargs)
		if character == "werewolf":
			return Werewolf(**kwargs)
		if character == "witch":
			return Witch(**kwargs)
		if character == "human":
			return Human(**kwargs)


class Character(Player):
	@classmethod
	def lynch(cls, character):
		return character.lynched()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def healed(self):
		self.state = "alive"

	def attacked_by_werewolves(self):
		self.state = "dead"
		# returning an even here doesn't work yet. self.game isn't referenced properly
		return event.EventFactory.create_event("dying", self.game)

	def lynched(self):
		self.state = "dead"
		print(self.__class__.__name__ + " was killed by an angry mob")

	def unique_ability_to_inherit(self):
		raise NotImplementedError

	def another_unique_ability_to_inherit(self):
		raise NotImplementedError


class Human(Character):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.character = "human"

	def attacked_by_werewolves(self):
		print(self.p_id+": Another defenseless human dies T.T")
		return super().attacked_by_werewolves()
		

	def healed(self):
		self.state = "alive"


class Witch(Human):
	# character specific class interacting with events
	@classmethod
	def heal(cls, character):
		return character.healed()

	def __init__(self, **kwargs):
		super().__init(**kwargs)
		self.character = "witch"


class Werewolf(Character):
	@classmethod
	def attack(cls, character):
		return character.attacked_by_werewolves()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.character = "werewolf"