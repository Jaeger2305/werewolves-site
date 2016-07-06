import warnings

from werewolves_game.server_scripting.user import Player
import werewolves_game.server_scripting.event as event

# causes reinitialisation right up to the User
# alternatively, changing .__class__ is possible. But sounds pretty bad practice. http://stackoverflow.com/questions/13280680/how-dangerous-is-setting-self-class-to-something-else
class CharacterFactory:
    @classmethod
    def create_character(cls, character, **kwargs):
        if character is None and 'p_id' in kwargs:
            myPlayer = Player(kwargs['p_id'])
            character = myPlayer.character
        # account for error here?

        if character == "unassigned":
            warnings.warn("Character created with no role. Could lead to undefined behaviour if player: "+kwargs['p_id']+" was expected to be a character. You have likely instantiated a game that hasn't begun yet.")
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
        self.save()
        return event.EventFactory.create_event("dying", self.g_id)

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
        self.used_heal = False
        self.used_kill = False

    def as_JSON(self, player_json={}):
        super().as_JSON(player_json)
        player_json['used_heal'] = self.used_heal
        player_json['used_kill'] = self.used_kill
        return json.dumps(player_json, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class Werewolf(Character):
    @classmethod
    def attack(cls, character):
        return character.attacked_by_werewolves()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.character = "werewolf"