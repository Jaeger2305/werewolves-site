# Tutorial... sort of
    # define your routers with a minimal route name, model and get_object/query_set
    # this is where the magic happens. In the front end javascript, I can call functions directly from the router, it's my main way of interacting with the server
    # You can use models to automate it, but I've chosen to go full manual using just the BaseRouter. The models were confusing.
    # it works both ways, I can send info to the router, which it can deal with and respond to. Security is obviously a big deal, never accept anything from the user without escaping the data!

    # to exchange data with the server, you can use the publish_data function (check game.py). This selects a channel and gives it a data_dict.
    # for the front end to access this data, the calling router must return the channel, which publish_data feeds the information through

    # Debugging:
        # pip install ipdb
        # https://www.safaribooksonline.com/blog/2014/11/18/intro-python-debugger/
        # import ipdb;ipdb.set_trace() (a breakpoint)
        # this opens in console when hit, where you can view what variables are being used
        # n[ext] goes to the next function
        # a[rgs] for current arguments
        # s[tep]
        # c[ontinue]
        # <object>.TAB = list methods/properties

        # this method doesn't work for ajax requests, but I guess you should KISS it anyway

        # can also writ to file if you have to
            #with open('logfile.txt', 'a') as log:
                #log.write(str(kwargs)+" are the kawrgs for get subscription channels\n")

    # Sessions
        # AJAX feeds lifepulse every 25 seconds from client
        # this reaches the session_handler view, which updates the session with latest access time
        # this is complemented by a PCB at the bottom of game.py (check_activity()) which is called through the session_handler router
            # the PCB cycles through all session data and deletes out of date ones, or alternatively a long time since the last life pulse
            # this is expensive, so I'm not sure if it's a good way of doing it
            # I could create a separate DB for players in game, and create a primary key for the sessions, then cycle through a JOIN table
            # I could also subset players (logged in, in game, guest) and have separate times for them
            # see http://stackoverflow.com/questions/235950/how-to-lookup-django-session-for-a-particular-user for helpful approaches

    # overwrite the subscription method?
    # bug: using channel as a key in the data dict passed in a subscribe call results in an empty kwarg. Very confusing.

    # okay, user specific channels implemented.
        # There are 3 aspects:
            # subscribe to channel:id (javascript),
            # publish to channel:id (game.py, publish_data()) and
            # add the channel to the get_subscription_channels list
    # get_subscription_channels is called whenever you [un]subscribe and filters what channels swampdragon has access to
    # You can add to the subscribed channels by using params in JS subscribe
    # Depending on the kwargs sent (javascript in subscribe/callrouter) you can dynamically filter
    # annoyingly this forces you to store session data in JS to pass in as custom kwargs
    # It's possible to publish to channels you're not subscribed to.
        #That means whenever publishing info, it needs to be check server side that you're allowed to do that. Yawn.

# TODO
    # Write list of subscribed channels I want to listen to in .txt
        # my game, the lobby, system messages, specific groups of players (werewolves/merlin etc), whispers
    # implement timeout for users in games and for the games themselves
        # ignore check_activity, I want the sessions to last 2 weeks, but can cleanup based on differing times of session['latest activity']
    # work out how to identify other players. Player ID's would need to be open, but I'd need to look up session data based on p_id :S
    # read this awesome post http://mrjoes.github.io/2013/06/21/python-realtime.html
    # feedback a countdown to game beginning to user, which starts immediate based on if all users have input "ready"
        # this requires retaining the callback ID for the iol and cancelling it
        # maybe add a state to the player class
    # use an object pool for the game so I don't have to keep allocating variables, or I could just rely on the redis cache.
    # callback queue class? Component in Player, Game etc.
    # messaging class? Component
    # a redis save/load static function class which accepts key and inputs in the form of a string and dict? Called by the classes that are saved to redis
    # privatise variables/add static functions
    # when game_state is called, create character specific objects.
        # Look at using a factory to generate different objects?    http://code.activestate.com/recipes/86900/
    # move periodic callbacks to a contained class
    # implement serialisation of objects http://stackoverflow.com/questions/3768895/python-how-to-make-a-class-json-serializable

    # Currently working on game.py Player class
        # Implement serialisers for the character classes (only player/user/game done)
        # add a filter method to hide data based on character status
        # have a standard parameter object to extend? Always contains session data for example on the client side JS
    # handle connection if player closes browser/session ends (started with the pulse_activity ajax)
    # convert from PCB to celery/CRON jobs? http://celery.readthedocs.org/en/latest/userguide/periodic-tasks.html
        # Or ask Stack overflow if this is really necessary
    # possible I add a flag to the objects, so at the end of a router, if the object's flag says update, I then save it to redis. Or i input it into the __del__ function
    # or I add custom redis saves that doesn't do the whole thing again. Still, not a lot for python to do to just serialise relatively small objects
    # timeout implemented by accessing iol from tornado.ioloop. This singleton would not be threadsafe, but the server runs on just one thread by default. Might have issues with scaling though
    # look into using swampdragon's session store? http://swampdragon.net/documentation/sessions/

# player.status = ['ingame', 'kicked', 'searching', 'finished', 'outgame']
# game.state = ['voting', 'lobby', 'discussion', 'starting']

# outline the different html elements I'll have for a rough idea where the information I'm giving is going to go
    # chatbox
    # events
    # timers
    # players

# BUGS

# Production checklist
    # using DB session store, needs to be cleared out regularly in production https://docs.djangoproject.com/en/1.9/ref/django-admin/#django-admin-clearsessions
    # change hget(keys) to scan (redis)

# short term:
    # continue code clean up
    # implement vote system/chat system
    # more matchmaking functions (host-requires forms)

# long term:
    # characters, rounds and event progression
    # track user logins

from swampdragon import route_handler
from swampdragon.route_handler import ModelPubRouter, BaseRouter
from werewolves_game.models import Notification
from werewolves_game.serializers import NotificationSerializer
from werewolves_game.server_scripting.game import *     # bad practice
from werewolves_game.server_scripting.user import Player, User
from werewolves_game.server_scripting.redis_util import *

from django.contrib.sessions.models import Session # redundant? Temp using it in session_handling

from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

class NotificationRouter(ModelPubRouter):
    route_name = 'notifications'
    valid_verbs = ['subscribe']
    model = Notification
    serializer_class = NotificationSerializer

class GameRouter(BaseRouter):
    route_name = 'game'
    valid_verbs = BaseRouter.valid_verbs + []

class LobbyRouter(BaseRouter):
    route_name = 'lobby'
    valid_verbs = BaseRouter.valid_verbs + ['messaging', 'session_handling', 'init', 'matchmaking']

    # all published methods pass through this func, the returned array of strings are the channels the messages are broadcast on.
    # defaults to first element (lobbyinfo)
    def get_subscription_channels(self, **kwargs):
        channels = ['lobbyinfo', 'playersInGame', 'sysmsg']
        
        # subscribing
        if 'session_key' in kwargs and kwargs['session_key'] is not None:
            session = SessionStore(session_key=kwargs['session_key'])
            if 'g_id' in session:
                channels.append('game:'+session['g_id'])
            if 'p_id' in session:
                channels.append('player:'+session['p_id'])

        # redundant?
        if 'output' in kwargs:
            if kwargs['output'] == 'player_list':
                return ['player_list:'+kwargs['g_id']]
            elif kwargs['output'].startswith("game:"):
                return ['game:'+kwargs['g_id']]

        # unsubscribing
        if ('action' in kwargs and kwargs['action'] == "unsubscribe"
            and 'listener' in kwargs and kwargs['listener'] == "game"
            ):
            unsub_channels = []
            for channel in channels:
                if channel.startswith(kwargs['listener']):
                    unsub_channels.append(channel)

            return unsub_channels

        return channels

    def init(self, **kwargs):
        broadcast_games()
        if "session_key" in kwargs:
            initUser = User(session_key=str(kwargs['session_key']))     # this ensures the user's session is stored with the p_id in redis, allowing subsequent calls to redis to require only the p_id
        else:
            return self.send({"error":"no session key supplied"})

    def session_handling(self, **kwargs):
        if 'action' not in kwargs:
            return self.send({"error":"no action given"})

        if kwargs['action'] == "delete":
            Session.objects.all().delete()
            return
        elif kwargs['action'] == "check":
            check_activity()
            return

    def matchmaking(self, **kwargs):
        if 'action' not in kwargs:
            return self.send({"error":"no action given"})

        session_data = SessionStore(session_key=kwargs['session_key'])

        if kwargs['action'] == "flush_db":
            ww_redis_db.flushall()     # use to clear redis of all keys to start afresh
            session_data.flush()
            response = "flushed!"

        if "p_id" in session_data:
            player = Player(session_data['p_id'])
        else:
            print("error: p_id not been assigned to session")

        if kwargs['action'] == "join_game":
            response = player.find_game(**kwargs)
        elif kwargs['action'] == "leave_game":
            response = player.leave_game(**kwargs)


        self.send(response)

    def messaging(self,**kwargs):
        # requires target, session
        if "session_key" not in kwargs:
            self.send("error: no sesh")
            return
        if "target" not in kwargs:
            self.send("no target given")
            return

        session_data = SessionStore(session_key=kwargs['session_key'])

        sender = session_data['p_id']

        if kwargs['target'] == "player":
            if "id" in kwargs:
                user = user(kwargs['id'])
                user.give_message(kwargs['msg'], sender, kwargs['target'], kwargs['time'])
            else:
                self.send("please give ID of the player")
                return
        elif kwargs['target'] == "game":
            #import ipdb;ipdb.set_trace()
            game = Game(session_data['g_id'])

            for user in game.players:
                user.give_message(kwargs['msg'], sender, kwargs['target'], kwargs['time'])

        elif kwargs['target'] == "world":
            data_dict = {}

            data_dict['message'] = kwargs['msg']
            data_dict['sender'] = sender
            data_dict['target'] = kwargs['target']
            data_dict['time'] = kwargs['time']
            data_dict['type'] = "message"
            data_dict['channel'] = "sysmsg"
            channel = "sysmsg"

            publish_data(channel, data_dict)
        #else:  # search through game given this grouping (witch, werewolf, humans etc.)

    def vote(self, **kwargs):
        raise NotImplementedError

# register router
route_handler.register(NotificationRouter)
route_handler.register(LobbyRouter)
route_handler.register(GameRouter)