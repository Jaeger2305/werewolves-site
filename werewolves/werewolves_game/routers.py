from django.contrib.sessions.models import Session # redundant? Temp using it in session_handling
from importlib import import_module
from django.conf import settings
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

from swampdragon import route_handler
from swampdragon.route_handler import ModelPubRouter, BaseRouter

from werewolves_game.server_scripting.game import *     # bad practice
from werewolves_game.server_scripting.user import Player, User
from werewolves_game.server_scripting.redis_util import *
from werewolves_game.server_scripting.custom_errors import ContinueError

class GameRouter(BaseRouter):
    route_name = 'game'
    valid_verbs = BaseRouter.valid_verbs + []

class LobbyRouter(BaseRouter):
    route_name = 'lobby'
    valid_verbs = BaseRouter.valid_verbs + ['broadcast_games', 'messaging', 'session_handling', 'init', 'matchmaking', 'vote', 'developer']

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
        response = {}
        response['message'] = "attempting to initiatilise player"

        if "session_key" in kwargs:
            init_user = User(session_key=str(kwargs['session_key']))     # this ensures the user's session is stored with the p_id in redis, allowing subsequent calls to redis to require only the p_id
            if(init_user.location == "ingame"):
                response['activeGame'] = init_user.session['g_id']
            response['userJson'] = init_user.as_JSON()
            response['message'] = "initialised user into Redis"
        else:
            response['error'] = "no session key supplied"

        return self.send(response)

    def developer(self, **kwargs):
        if kwargs['action'] == "test_game":
            for x in range(1,int(kwargs['player_count'])):
                player = Player(session_key=User(session_key=x).session_key)
                player.find_game()

            myPlayer = Player(session_key=kwargs['session_key'])
            myPlayer.find_game()

        elif kwargs['action'] == "ask_update":
            myPlayer = Player(session_key=kwargs['session_key'])
            myGame = Game(session_key=kwargs['session_key'])

            publish_dict = GameManager.publish_detailed_game(g_id=myGame.g_id, p_id=myPlayer.p_id)
            #filtered_json = myGame.filter_JSON(full_json, myPlayer.knows_about) # include this somehow?

            self.send(publish_dict)

        elif kwargs['action'] == "ask_shallow_update_on_all_games": # call out to Game Manager shallow update
            games_dict = {}
            data_dict = {}
            publish_dict = GameManager.publish_all_games()

            self.send(publish_dict)

        elif kwargs['action'] == "gain_info":
            if 'attribute_filter' in kwargs:
                attribute_filter = kwargs['attribute_filter'].split(",")
            else:
                attribute_filter = ['state']

            myGame = Game(session_key=kwargs['session_key'])
            myPlayer = myGame.players[0]

            print(myPlayer.knows_about)
            myPlayer.gain_info(attribute_filter=attribute_filter, info_player=myGame.players[1])
            print(myPlayer.knows_about)
            self.send("added info on player: " + myGame.players[1].p_id + "\n for this player: "+myPlayer.p_id)

        elif kwargs['action'] == "lose_info":
            if 'attribute_filter' in kwargs:
                attribute_filter = kwargs['attribute_filter'].split(",")
            else:
                attribute_filter = ['state']

            myGame = Game(session_key=kwargs['session_key'])
            myPlayer = myGame.players[0]

            print(myPlayer.knows_about)
            myPlayer.lose_info(attribute_filter=attribute_filter, info_player=myGame.players[1])
            print(myPlayer.knows_about)

            self.send("lost info on player: " + myGame.players[1].p_id + "\n for this player: "+myPlayer.p_id)


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
        response = {}   # an object used to return information to the client directly.
        if 'action' not in kwargs:
            return self.send({"error":"no action given"})

        session_data = SessionStore(session_key=kwargs['session_key'])

        if kwargs['action'] == "flush_db":
            ww_redis_db.flushall()     # use to clear redis of all keys to start afresh
            session_data.flush()
            self.send("flushed!")
            return

                                                            ############################################################
                                                            # Initialise player
                                                            ############################################################
        if "p_id" in session_data:
            player = Player(session_data['p_id'])
        else:
            print("error: p_id not been assigned to session")
            raise TypeError

                                                            ############################################################
                                                            # Join game
                                                            ############################################################
        if kwargs['action'] == "join_game":
            response = player.find_game(**kwargs)   # this should really be done throug the game manager

                                                            ############################################################
                                                            # Leave game
                                                            ############################################################
        elif kwargs['action'] == "leave_game":
            try:
                if 'g_id' in kwargs:
                    player_game = Game(kwargs['g_id'])
                elif hasattr(player, "g_id"):
                    player_game = Game(player.g_id)
                elif 'g_id' in self.session:
                    player_game = Game(player.session['g_id'])
                    log_handler.log(
                        log_type    = "INFO",
                        log_code    = "Player",
                        log_message = "g_id was passed via session and not via kwargs",
                        log_detail  = 7,
                        context_id  = player.p_id
                    )
                elif not player.is_ingame():
                    response['error'] = "Player not currently in a game."
                    log_handler.log(
                        log_type    = "ERROR",
                        log_code    = "Player",
                        log_message = "This player tried to leave their game when they weren't in any game",
                        log_detail  = 3,
                        context_id  = player.p_id
                    )
                    raise ValueError ("Player not current in a game")
                else:
                    response['error'] = "Game not found"
                    log_handler.log(
                        log_type    = "ERROR",
                        log_code    = "Player",
                        log_message = "No game could be found that is associate with this player",
                        log_detail  = 3,
                        context_id  = player.p_id
                    )
                    raise ValueError ("Game not found")

                if player.p_id in player_game.players:
                    player_game.remove_player(leaving_player=player)

                    response['response'] = "Player removed from game"
                else:
                    response['error'] = "Player not found in game: "+player_game.g_id
                    log_handler.log(
                        log_type        = "ERROR",
                        log_code        = "Player",
                        log_message     = "Could not find this player in the game "+player_game.g_id,
                        log_detail      = 4,
                        context_id      = player.p_id
                    )
            except ValueError:
                log_handler.log(
                    log_type        = "ERROR",
                    log_code        = "Player",
                    log_message     = "Could not find this player in the game "+player_game.g_id,
                    log_detail      = 4,
                    context_id      = player.p_id
                )

                                                            ############################################################
                                                            # Create game
                                                            ############################################################
        elif kwargs['action'] == "create_game":
            user_config = {}
            if 'config' in kwargs:
                user_config = kwargs['config']

            newGame = Game(config=user_config)

            if player.is_ingame():
                Game(player.g_id).remove_player(player.p_id)

            response = newGame.add_player(player.p_id)


                                                            ############################################################
                                                            # Send response to client
                                                            ############################################################
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
        myGame = Game(session_data['g_id'])
        myGame.event_queue[0].add_vote(kwargs['p_id'])
        raise NotImplementedError

    def broadcast_games(self, *kwargs):
        return self.send(broadcast_games())

# register router
route_handler.register(LobbyRouter)
route_handler.register(GameRouter)