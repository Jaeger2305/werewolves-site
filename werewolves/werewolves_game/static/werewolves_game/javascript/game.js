/*********************************************************
*
* Game.js
* Mimics the game object represented on the server
* changes to the server are reflected on this object, which then updates the relevant html
*
 ***********************************************************/

function Game(g_id, players, state){
	this.g_id = g_id;
	this.players = players;
	this.state = state;
}

function Player(p_id, name, state, character){
	this.p_id = p_id;
	this.name = name;
	this.state = state;
	this.character = character;
}

var games_list = [];
var players_list = [];