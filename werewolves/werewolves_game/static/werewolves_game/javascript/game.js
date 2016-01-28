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
	$("#games_list").html("<table>");
	for (game of this.games_list){
		$("#game_list").append("<tr><td>"+game.g_id+"</td>");
		$("#game_list").append("<td>"+game.players+"</td></tr>");
	}
	$("#game_list").append("</table>");
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
		//$("#player_list").append("<tr><td>"+player.p_id+"</td></tr>"));
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

game_manager = new Game_Manager();

var player_list = [];