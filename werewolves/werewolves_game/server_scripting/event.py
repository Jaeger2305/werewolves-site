import uuid
import warnings
import weakref
import json
from collections import Counter
from random import shuffle

from swampdragon.pubsub_providers.data_publisher import publish_data
from tornado.ioloop import IOLoop

import werewolves_game.server_scripting as wwss
from werewolves_game.server_scripting.redis_util import *
from werewolves_game.server_scripting.callback_handling import callback_handler
from werewolves_game.server_scripting.log import log_handler

# global callback handling/cancelling singleton
# class callback_handling:

# More events can be added here. Methods of characters can call this method to generate custom events.
class EventFactory():
    @classmethod
    def create_event(cls, e_type, g_id, parent_game=None):
        if not parent_game:
            parent_game = wwss.game.Game(g_id)

        if e_type == "night":
            return Event(   
                            g_id,
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Werewolf, "alive"])],
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Human, "alive"])],
                            cls.lookup_action(e_type), e_type
                        )
        if e_type == "day":
            return Event(
                            g_id,
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Character, "alive"])],
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Character, "alive"])],
                            cls.lookup_action(e_type), e_type
                        )
        if e_type == "dying":
            return Event(
                            g_id,
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Witch, "alive"])],
                            [player.p_id for player in parent_game.get_groups(["dead", "last_event"])],
                            cls.lookup_action(e_type), e_type
                        )
        if e_type == "witch_save":
            raise NotImplementedError
            return Event(
                            g_id,
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Human])],
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Witch])],
                            cls.lookup_action(e_type),
                            e_type
                        )
        if e_type == "witch_kill":
            raise NotImplementedError
            return Event(
                            g_id,
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Character])],
                            [player.p_id for player in parent_game.get_groups([wwss.characters.Witch])],
                            cls.lookup_action(e_type),
                            e_type
                        )

    @classmethod
    def event_from_redis(cls, g_id, instigators, subjects, e_type, result_subjects, votes, e_id, voting_callback_reference=None):
        return Event(g_id, instigators, subjects, cls.lookup_action(e_type), e_type, result_subjects, votes, e_id, voting_callback_reference)

    @classmethod
    def lookup_action(cls, e_type):
        if e_type == "night":
            return wwss.characters.Werewolf.attack
        if e_type == "day":
            return wwss.characters.Human.lynch
        if e_type == "dying":
            return wwss.characters.Witch.heal


# Handles broadcasting and vote hosting of the event
# for selective info, use the Game class to filter
class Event():
    def __init__(self, g_id, instigators, subjects, action, e_type, result_subjects=[], votes=[], e_id=None, voting_callback_reference=None):
        self.subjects                   = subjects			# list of those the events affects
        self.instigators                = instigators		# list of those starting the event
        self.action                     = action			# function that will implement the effect
        self.g_id                       = g_id
        self.e_type                     = e_type
        self.result_subjects            = result_subjects
        self.votes                      = votes
        self.voting_callback_reference  = voting_callback_reference
        self.action_without_instigators = False

        if not e_id:		# not from redis
            e_id                    = str(uuid.uuid4())
            self.result_subjects    = []	# forces to list, otherwise it's kept as null

        self.e_id =  e_id
        self.save()
        return

    def __eq__(self, other):
        return self.e_id == other.e_id

    def save(self):
        ww_redis_db.hset("event:"+self.e_id, "game", self.g_id)
        ww_redis_db.hset("event:"+self.e_id, "e_type", self.e_type)
        ww_redis_db.hset("event:"+self.e_id, "instigators", "|".join(self.instigators))
        ww_redis_db.hset("event:"+self.e_id, "subjects", "|".join(self.subjects))
        ww_redis_db.hset("event:"+self.e_id, "result_subjects", "|".join(self.result_subjects))
        ww_redis_db.hset("event:"+self.e_id, "votes", "|".join(self.votes))

        ww_redis_db.hset("event:"+self.e_id, "voting_callback_reference", self.voting_callback_reference)

    @staticmethod   # g_id should be redundant... shouldn't it always be with e_id?
    def load(g_id, e_id):
        redis_event = ww_redis_db.hgetall("event:"+e_id)
        redis_event = {k.decode('utf8'): v.decode('utf8') for k, v in redis_event.items()}

        instigators = subjects = result_subjects = votes = []
        voting_callback_reference = None

        if not redis_event:
            raise ValueError("couldn't load event from redis with e_id: " + e_id)

        if redis_event["game"]:
            g_id            = redis_event["game"]
        if redis_event["instigators"]:
            instigators     = redis_event["instigators"].split("|")
        if redis_event["subjects"]:
            subjects        = redis_event["subjects"].split("|")
        if redis_event["result_subjects"]:
            result_subjects = redis_event["result_subjects"].split("|")

        # creates new users based on p_id. Not v memory efficient. Check p_ids with game.players and see if you can reference them?
        # instigators = [wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id) for p_id in instigators]
        # subjects = [wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id) for p_id in subjects]
        # result_subjects = [wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id) for p_id in result_subjects]

        #instigators = [self.game.get_groups(p_id)[0] for p_id in instigators]
        #subjects = [self.game.get_groups(p_id)[0] for p_id in subjects]
        #result_subjects = [self.game.get_groups(p_id)[0] for p_id in result_subjects]
        if redis_event["votes"]:        
            votes = redis_event["votes"].split("|")

        if redis_event["voting_callback_reference"]:
            voting_callback_reference = redis_event["voting_callback_reference"]

        return EventFactory.event_from_redis(g_id, instigators, subjects, redis_event["e_type"], result_subjects, votes, e_id, voting_callback_reference=voting_callback_reference)

    def as_JSON(self):
        event_json = {}
        event_json['e_id'] = self.e_id
        event_json['e_type'] = self.e_type

        event_json['instigators'] = self.e_type
        event_json['subjects'] = self.e_type
        event_json['result_subjects'] = self.e_type

        instigators_json = {}
        for p_id in self.instigators:
            instigators_json[p_id] = wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id).as_JSON()

        subjects_json = {}
        for p_id in self.subjects:
            subjects_json[p_id] = wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id).as_JSON()

        result_subjects_json = {}
        for p_id in self.result_subjects:
            result_subjects_json[p_id] = wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id).as_JSON()

        event_json['votes'] = self.votes

        # assuming event action can be inferred from e_type. Therefore not included in JSON.

        event_json['instigators'] = instigators_json
        event_json['subjects'] = subjects_json
        event_json['result_subjects'] = result_subjects_json

        return json.dumps(event_json, sort_keys=True, indent=4)

    def start(self):
        log_type    = "INFO"
        log_code    = "Event"
        log_message = "Subjects of the event: " + str(self.subjects) + ". Instigators are: " + str(self.instigators)
        log_detail  = 3
        context_id  = self.e_id

        log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)

        if not self.subjects or not self.instigators:
            self.finish_event()     # has a 3 second pause to allow async to catch up and prevent needless call stack preservation
            return
        
        parent_game = wwss.game.Game(self.g_id)
        parent_game.change_state("new_event")

        if len(self.subjects) > 1 or len(self.instigators) > 1:
            if len(self.subjects) != 1 and len(self.instigators) != 1:
                log_type    = "INFO"
                log_code    = "Event"
                log_message = "Multiple options are available and a vote must be held."
                log_detail  = 5
                context_id  = self.e_id

                log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)
                self.hold_vote()

        if len(self.subjects) == 1:
            self.result_subjects = self.subjects

            log_type    = "INFO"
            log_code    = "Event"
            log_message = "Only one option found, beginning immediately."
            log_detail  = 5
            context_id  = self.e_id

            log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)
            self.finish_event()

    def hold_vote(self):
        parent_game = wwss.game.Game(self.g_id)
        parent_game.change_state("voting")

        callback_handle = IOLoop.current().call_later(8, Event.vote_result, parent_game.g_id, self.e_id)
        self.voting_callback_reference = callback_handler.add_callback(self.e_id, callback_handle)
        self.save()

    @staticmethod
    def add_vote(g_id, e_id, p_id_vote, voting_by_p_id=None):
        voting_event = Event.load(g_id, e_id)
        parent_game = wwss.game.Game(g_id)

        log_type    = "INFO"
        log_code    = "Event"
        log_message = "A player just voted for " + p_id_vote
        log_detail  = 7
        context_id  = self.e_id

        log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)

        voting_event.votes.append(p_id_vote)

        if len(voting_event.votes) == len(voting_event.voters):
            parent_game.change_state("finished_voting")
            voting_event.vote_result()

    # perhaps unnecessary to split out from finish_event, but might be useful in the future to publish some unrelated data here
    @staticmethod
    def vote_result(g_id, e_id):
        parent_game = wwss.game.Game(g_id)
        voting_event = Event.load(g_id, e_id)
        callback_handler.remove_callback(voting_event.e_id, voting_event.voting_callback_reference)

        if voting_event.votes:
            p_id_most_common = Counter(voting_event.votes).most_common(1)

            log_type    = "INFO"
            log_code    = "Event"
            log_message = "Most common vote was" + p_id_most_common
            log_detail  = 5
            context_id  = self.e_id

            log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)

            voting_event.result_subjects = [p_id_most_common]
        else:
            shuffle(voting_event.subjects)

            log_type    = "INFO"
            log_code    = "Event"
            log_message = "No votes were given, a random choice has been selected: " + voting_event.subjects[0]
            log_detail  = 5
            context_id  = e_id

            log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)

            voting_event.result_subjects = [voting_event.subjects[0]]

        parent_game.change_state("finished_voting")
        voting_event.save()
        voting_event.finish_event()
        return

    def finish_event(self):
        parent_game = wwss.game.Game(self.g_id)

        log_type    = "INFO"
        log_code    = "Event"
        log_message = "Result subjects of the event:"+str(self.result_subjects)
        log_detail  = 5
        context_id  = self.e_id

        log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)

        if self.result_subjects and (self.instigators or self.action_without_instigators):		# only add to history if there is an effect
            parent_game.archive_event(self.e_id)
            log_handler.log(
                log_type        = "INFO",
                log_code        = "Event",
                log_message     = "Event has been archived",
                log_detail      = 3,
                context_id      = self.e_id
            )
        else:
            parent_game.delete_event("event_queue", self.e_id)

            log_type    = "INFO"
            log_code    = "Event"
            log_message = "This event has been deleted from its game's event_queue"
            log_detail  = 5
            context_id  = self.e_id

            log_handler.log(log_type=log_type, log_code=log_code, log_message=log_message, log_detail=log_detail, context_id=context_id)

            ww_redis_db.delete("event:"+self.e_id)
        
        for p_id in self.result_subjects:	# new events queued will be in reverse order to the order they were added to subjects
            player = wwss.characters.CharacterFactory.create_character(character=None, p_id=p_id)
            result = self.action(player)
            if result and isinstance(result, Event):
                result = [result]   # forces into array to allow multiple events by default
            if result and any(isinstance(e, Event) for e in result):    # if result contains any events
                for event in result:
                    [parent_game.add_event(event.e_id, at_front=True) for event in result if isinstance(event, Event)]		# adds events with the same order they were returned

        if parent_game.get_winners():
            parent_game.change_state("game_finished")
        else:
            parent_game.change_state("waiting")