from werewolves_game.server_scripting.user import Player

class Character(Player):
	# character specific class interacting with events
	team = ["standard"]

	def __init__(self, p_id):
		super().__init__(p_id)

	def vote(p_id):
		dosomething = "nothing"

	def attacked():
		self.state = "dead"


class Witch(Character):
	# character specific class interacting with events
	team = ["standard"]
	action = "nothing"

	def __init__(self, p_id):
		super().__init(p_id)

	def vote(p_id):
		self.action = "something"


class Werewolf(Character):
	# special characters
	team = ["werewolves"]

	def __init__(self, p_id):
		super().__init__(p_id)

	def kill(p_id):
		target = Player(p_id)
		target.state = "dead"