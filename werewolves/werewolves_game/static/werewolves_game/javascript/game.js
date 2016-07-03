/*********************************************************
*
* Game.js
* Mimics the game object represented on the server
* changes to the server are reflected on this object, which then updates the relevant HTML
* global gameManager is used to add and manipulate the visible games
* currently only used in receiving lobby/game specific channel messages
* 
* TODO:
*	Look into Angular JS for hooking into HTML instead of arbitrary jquery id placement
*	Implement players
*
 ***********************************************************/

/***********************************************************************************************************************
* GameManager methods
***********************************************************************************************************************/
function GameManager(){
    this.games_list = [];
    this.activeGame = "";
}

GameManager.prototype.display = function(){
    $("#game_list, #player_list").html("<table>");
    for (game of this.games_list){
        $("#game_list").append("<tr><td>" + game.g_id + "</td>");
        if (this.activeGame === game.g_id){
            game.display();
        }
    }
    $("#game_list, #player_list").append("</table>");
}

GameManager.prototype.add_game = function(game){
    this.games_list.push(game);
}

GameManager.prototype.remove_game = function(myGame){
    for (var i = this.games_list.length-1; i >= 0; i--){
        if (game.g_id === myGame.g_id)
            this.games_list.splice(i, 1);
    }
}

GameManager.prototype.find = function(g_id){
    for (game of this.games_list){
        if (game.g_id === g_id)
            return game;
    }
    return false;
}

GameManager.prototype.makeActiveGame = function(g_id){
    this.activeGame = g_id;
}


/***********************************************************************************************************************
* Game methods
***********************************************************************************************************************/
function Game(gameJson, g_id, players, state) {
    if (gameJson !== undefined) {
        if (typeof (gameJson) === "string")     // fails if string created as object, better than nothing
            newGame = JSON.parse(gameJson);
        else {
            newGame = gameJson      // more appropriate naming
        }

        g_id = newGame.g_id;
        players = newGame.players;
        state = newGame.state;
        event_queue = newGame.event_queue;
        event_history = newGame.event_history;
    }

    this.g_id = g_id;
    this.state = state;
    this.players = [];
    for (var playerJson in players) {
        this.players.push(new Player(players[playerJson]));
    }

    if ($.inArray(activeUser.p_id, gameJson.players)) {
        gameManager.makeActiveGame(this.g_id)
    }
}

Game.prototype.update = function (gameJson) {
    if ('g_id' in gameJson) { this.g_id = gameJson.g_id; }
    if ('state' in gameJson) { this.state = gameJson.state; }
    if ('g_round' in gameJson) { this.g_round = gameJson.g_round; }
    if ('witch_enabled' in gameJson) { this.witchEnabled = gameJson.witch_enabled; }
    if ('mystic_enabled' in gameJson) { this.mysticEnabled = gameJson.mystic_enabled; }
    if ('players' in gameJson) {
        this.players = []
        for (var refresh_player_json in gameJson.players) {
            this.players.push(new Player(gameJson.players[refresh_player_json]));
        }
    }
    //if ('event_history' in json) {
    //    this.event_history = []
    //    for (var refresh_event_history_json in json.event_history) {
    //        this.event_history.push(new Event(refresh_event_history_json))
    //    }
    //}
    //if ('event_queue' in json) {
    //    this.event_queue = []
    //    for (var refresh_event_queue_json in json.event_queue) {
    //        this.event_queue.push(new Event(refresh_event_queue_json))
    //    }
    //}
    if ($.inArray(activeUser.p_id, gameJson.players)) {
        gameManager.makeActiveGame(this.g_id)
    }
}

Game.prototype.addPlayer = function (playerJson) {
    player = JSON.parse(playerJson);
    if (player.p_id === activeUser.p_id) {
        gameManager.activeGame = this.g_id;
    }
}

Game.prototype.display = function(){
    $("#player_list").html("");
    for (var player of this.players){
        console.log(player);
        $("#player_list").append(
            "<tr>" +
                "<td>" + player.p_id + "</td>" +
                "<td>" + player.name + "</td>" +
                "<td>" + player.state + "</td>" +
                "<td>" + player.character + "</td>" +
            "</tr>"
        );
    }
}

/***********************************************************************************************************************
* User methods
***********************************************************************************************************************/
function User(userJson) {
    if (typeof (userJson) === "string") {
        userJson = JSON.parse(userJson)
    }
    this.location = userJson.location;
    this.p_id = userJson.p_id;
    if ('g_id' in userJson) {
        this.g_id = userJson.g_id;    // unnecessary/unused?
    }
    else {
        this.g_id = null;
    }
}

/***********************************************************************************************************************
* Player methods
***********************************************************************************************************************/
function Player(playerJson) {
    // ensure json is parsed
    if (typeof (playerJson) === "string") {
        playerJson = JSON.parse(playerJson)
    }
    
    this.p_id = playerJson.p_id;
    this.name = playerJson.name;
    this.state = playerJson.state;
    this.character = playerJson.character;
}

Player.prototype.update = function (playerJson) {
    if ('p_id' in playerJson) { this.p_id = playerJson.p_id; }
    if ('name' in playerJson) { this.name = playerJson.name; }
    if ('state' in playerJson) { this.state = playerJson.state; }
    if ('character' in playerJson) { this.character= playerJson.character; }
}


                                                            /***********************************************************
                                                            * Message methods
                                                            ***********************************************************/
Player.prototype.message = function(msg, targetPID){
    parameters = {"msg":msg, "target":targetPID, "session_key": session_key};
    swampdragon.callRouter('messaging', 'lobby', parameters, function(context, data){
        console.log(data);
        $('#server_updates').prepend("<div class='message'>"+data+"</div>");
    });
}

Player.prototype.receive_message = function(msg, sender, target, time){
    var constructed = "";
    constructed = "<div class=message_target_"+target+">["+time+"] "+sender+": "+msg+"</div>";
    $("#chatbox_read").append(constructed);
}



/***********************************************************************************************************************
* Global variables
***********************************************************************************************************************/
var gameManager = new GameManager();

var activeUser; // initialised in swampdragon init router call

var selected_players = [];


/***********************************************************************************************************************
* Plugins and snippets
***********************************************************************************************************************/
// credit to adamb http://stackoverflow.com/a/13866517/2276412
// makes a span editable on double click
$.fn.extend({
    editable: function() {
        var that = this,
            $edittextbox = $('<input type="text"></input>').css('min-width', that.width()),
            submitChanges = function() {
                that.html($edittextbox.val());
                that.show();
                that.trigger('editsubmit', [that.html()]);
                $(document).off('click', submitChanges);
                $edittextbox.detach();
            },
            tempVal;
        $edittextbox.click(function(event) {
            event.stopPropagation();
        });

        that.dblclick(function(e) {
            tempVal = that.html();
            $edittextbox.val(tempVal).insertBefore(that).off("keypress").on('keypress', function(e) {
                if ($(this).val() !== '') {
                    var code = (e.keyCode ? e.keyCode : e.which);
                    if (code == 13) {
                        submitChanges();
                    }
                }
            });
            that.hide();
            $(document).one("click", submitChanges);
        });
        return that;
    }
});