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
            #log = open('logfile.txt', 'a')
            #log.write(str(kwargs)+" are the kawrgs for get subscription channels\n")

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
    # separate users and game players.
    # Write list of subscribed channels I want to listen to in .txt
        # my game, the lobby, system messages, specific groups of players (werewolves/merlin etc), whispers
    # unsubscribe functionality, ie. from channels when leaving game
    # implement timeout for users in games and for the games themselves
        # ignore check_activity, I want the sessions to last 2 weeks, but can cleanup based on differing times of session['latest activity']
    # work out how to identify other players. Player ID's would need to be open, but I'd need to look up session data based on p_id :S

    # Currently working on game.py Player class
        # the plan is to move it all under the player object, it's not thoroughly tested though
        # Also need to reply and interpret better with the client-server interactions (JSON array given)
        # have a standard parameter object to extend? Always contains session data for example on the client side JS
        # set up inheritance and move session_data into user class
    # handle connection if player closes browser/session ends (started with the pulse_activity ajax)
    # convert from PCB to celery/CRON jobs

# look into using swampdragon's session store? http://swampdragon.net/documentation/sessions/

# player.status = ['ingame', 'kicked', 'searching', 'finished', 'outgame']
    
# BUGS
    # Joining/leaving games causes players in game to creep up. Probably something to do with the new status var in the session/

# Sessions
    # AJAX feeds lifepulse every 25 seconds from client
    # this reaches the session_handler view, which updates the session with latest access time
    # this is complemented by a PCB at the bottom of game.py (check_activity()) which is called through the session_handler router
        # the PCB cycles through all session data and deletes out of date ones, or alternatively a long time since the last life pulse
        # this is expensive, so I'm not sure if it's a good way of doing it
        # I could create a separate DB for players in game, and create a primary key for the sessions, then cycle through a JOIN table
        # I could also subset players (logged in, in game, guest) and have separate times for them
        # see http://stackoverflow.com/questions/235950/how-to-lookup-django-session-for-a-particular-user for helpful approaches

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
from werewolves_game.server_scripting.game import *
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
    valid_verbs = BaseRouter.valid_verbs + ['messaging', 'session_handling', 'pushMessage', 'get_players', 'get_games_list', 'join_game', 'leave_game', 'matchmaking', 'messaging']

    # all published methods pass through this func, the returned array of strings are the channels the messages are broadcast on.
    # defaults to first element (lobbyinfo)
    def get_subscription_channels(self, **kwargs):
        broadcast_games()   # should move this to a separate init router

        channels = ['lobbyinfo', 'playersInGame', 'sysmsg']
        
        # subscribing
        if 'session_key' in kwargs.keys() and kwargs['session_key'] is not None:
            session = SessionStore(session_key=kwargs['session_key'])
            if 'g_id' in session.keys():
                channels.append('game:'+session['g_id'])
            if 'p_id' in session.keys():
                channels.append('player:'+session['p_id'])

        # redundant?
        if 'output' in kwargs:
            if kwargs['output'] == 'player_list':
                return ['player_list:'+kwargs['g_id']]
            elif kwargs['output'].startswith("game:"):
                return ['game:'+kwargs['g_id']]

        # unsubscribing
        if ('action' in kwargs.keys() and kwargs['action'] == "unsubscribe"
            and 'listener' in kwargs.keys() and kwargs['listener'] == "game"
            ):
            unsub_channels = []
            for channel in channels:
                if channel.startswith(kwargs['listener']):
                    unsub_channels.append(channel)

            return unsub_channels

        return channels

    def session_handling(self, **kwargs):
        if 'action' not in kwargs.keys():
            return self.send({"error":"no action given"})

        if kwargs['action'] == "delete":
            Session.objects.all().delete()
            return
        elif kwargs['action'] == "check":
            check_activity()
            return

    def matchmaking(self, **kwargs):
        if 'action' not in kwargs.keys():
            return self.send({"error":"no action given"})

        session_data = SessionStore(session_key=kwargs['session_key'])

        player = Player(kwargs['session_key'])

        if kwargs['action'] == "join_game":
            response = player.find_game(**kwargs)
        elif kwargs['action'] == "leave_game":
            response = player.leave_game(**kwargs)
        if kwargs['action'] == "flush_db":
            ww_redis_db.flushall()     # use to clear redis of all keys to start afresh
            session_data.flush()
            response = "flushed!"

        self.send(response)

    def messaging(self, **kwargs):
        player = Player(kwargs['session_key'])
        player.push_message(**kwargs)
        self.send("hi")

    def pushMessage(self, **kwargs):
        push_system_message(kwargs["message"])

    def get_players(self, **kwargs):
        broadcast_players(kwargs['g_id'])

    def get_games_list(self, **kwargs):
        broadcast_games()

    def create_game(self, **kwargs):
        return

    def join_game(self, **kwargs):
        session_data = SessionStore(session_key=kwargs['session_key'])
        log.write("kwargs in routers:"+str(kwargs.items())+"\n")

        player = Player(kwargs['session_key'])

        response = player.find_game(**kwargs)
        self.send(response)

    def leave_game(self, **kwargs):
        session_data = SessionStore(session_key=kwargs['session_key'])

        session_data['fry'] = 'try'
        session_data.save()
        log = open("logfile.txt", "a")
        log.write(str(session_data.values())+"\n"+str(session_data.session_key)+"\n")

        if 'p_id' in session_data.keys():
            log = open("logfile.txt", "a")
            log.write("\nfound p_id in session\n"+session_data['p_id'])

            myPlayer = Player(kwargs['session_key'])
            self.send(myPlayer.leave_game())

# register router
route_handler.register(NotificationRouter)
route_handler.register(LobbyRouter)
route_handler.register(GameRouter)