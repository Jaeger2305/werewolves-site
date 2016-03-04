/*********************************************************
*
* Game.js
* Mimics the game object represented on the server
* changes to the server are reflected on this object, which then updates the relevant HTML
* global game_manager is used to add and manipulate the visible games
* currently only used in receiving lobby/game specific channel messages
* 
* TODO:
*	Look into Angular JS for hooking into HTML instead of arbitrary jquery id placement
*	Implement players
*
 ***********************************************************/

function Game_Manager(){
	this.games_list = [];
}

Game_Manager.prototype.display = function(){
	$("#games_list, #player_list").html("<table>");
	for (game of this.games_list){
		$("#game_list").append("<tr><td>"+game.g_id+"</td>");
		$("#player_list").append("<td>"+game.players+"</td></tr>");
	}
	$("#game_list, #player_list").append("</table>");
}

Game_Manager.prototype.add_game = function(game){
	this.games_list.push(game);
}

Game_Manager.prototype.remove_game = function(myGame){
	for (var i = this.games_list.length-1; i >= 0; i--){
		if (game.g_id === myGame.g_id)
			this.games_list.splice(i, 1);
	}
}

Game_Manager.prototype.find = function(g_id){
	for (game of this.games_list){
		if (game.g_id === g_id)
			return game;
	}
	return false;
}



function Game(json, g_id, players, state){
	if (json !== undefined){
		if (typeof(json) === "string")		// fails if string created as object, better than nothing
			json = JSON.parse(json);

		g_id = json.g_id;
		players = json.players;
		state = json.state;
		event_queue = json.event_queue;
		event_history = json.event_history;
	}

	this.g_id = g_id;
	this.players = [];
	for (var player in players){
		this.players.push(new Player(
			player.p_id, 
			player.name,
			player.state,
			player.character)
		);
	}
	this.state = state;

	game_manager.add_game(this);
}

Game.prototype.update = function(json){
	if ('g_id' in json){	this.g_id = json.g_id;	}
	if ('state' in json){	this.state = json.state;	}
}

Game.prototype.display = function(){
	$("#player_list").html("");
	for (var player of this.players){
		console.log(player);
		$("#player_list").append("<tr><td>"+player.p_id+"</td></tr>");
	}
}

function Player(p_id, name, state, character){
	this.p_id = p_id;
	this.name = name;
	this.state = state;
	this.character = character;
}

Player.prototype.update = function(json){
	if ('p_id' in json){	this.p_id = json.p_id;	}
	if ('state' in json){	this.state = json.state;	}
}

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


game_manager = new Game_Manager();

myPlayer = new Player();

var selected_players = [];


// plugins
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