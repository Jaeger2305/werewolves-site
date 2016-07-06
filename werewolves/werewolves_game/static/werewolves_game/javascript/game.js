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
    this.gameList = [];
    this.activeGame = "";
}

GameManager.prototype.display = function(){
    $("#game_list, #player_list").html("<table>");
    for (game of this.gameList) {
        $("#game_list").append("<tr><td>" + game.g_id + "</td>");
        if (this.activeGame === game.g_id){
            game.display();
        }
    }
    $("#game_list, #player_list").append("</table>");
}

GameManager.prototype.add_game = function(game){
    this.gameList.push(game);
}

GameManager.prototype.remove_game = function(myGame){
    for (var i = this.gameList.length - 1; i >= 0; i--) {
        if (game.g_id === myGame.g_id)
            this.gameList.splice(i, 1);
    }
}

GameManager.prototype.find = function(g_id){
    for (game of this.gameList) {
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

    this.event_queue = []
    for (var refresh_event_queue_json in newGame.event_queue) {
        this.event_queue.push(new Event(newGame.event_queue[refresh_event_queue_json], this))
    }

    this.event_history = []
    for (var refresh_event_history_json in newGame.event_history) {
        this.event_history.push(new Event(newGame.event_history[refresh_event_history_json], this))
    }

    if ($.inArray(activeUser.p_id, newGame.players)) {
        gameManager.makeActiveGame(this.g_id)
    }
}

Game.prototype.update = function (gameJson) {
    if (typeof (gameJson) === "string")     // fails if string created as object, better than nothing
        newGame = JSON.parse(gameJson);
    else {
        newGame = gameJson      // more appropriate naming
    }
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
    if ('event_history' in gameJson) {
        this.event_history = []
        for (var refresh_event_history_json in gameJson.event_history) {
            this.event_history.push(new Event(newGame.event_history[refresh_event_history_json], this))
        }
    }
    if ('event_queue' in gameJson) {
        this.event_queue = []
        for (var refresh_event_queue_json in gameJson.event_queue) {
            this.event_queue.push(new Event(newGame.event_queue[refresh_event_queue_json], this))
        }
    }
    if ($.inArray(activeUser.p_id, gameJson.players)) {
        gameManager.makeActiveGame(this.g_id)
    }
}

Game.prototype.addPlayer = function (playerJson) {
    var player = JSON.parse(playerJson);
    if (player.p_id === activeUser.p_id) {
        gameManager.activeGame = this.g_id;
    }
}

// example call:
    //var p_ids = Object.keys(newEvent.subjects);
    //for (var i = p_ids.length - 1; i >= 0; i--) {
    //    this.subjects.push(parentGame.getIndividuals(selectionPool = parentGame.players, filters = [p_ids[i]], expectedCount = 1));
    //}
Game.prototype.getGroups = function (groupsOfFilters, expectedCount) {
    var selectionPool = this.players;   // the pool of players to select from
    var selectedPlayers = [];   // the results of a single filterGroup
    var groupList = []; // the list of players returned after combining all of the groups after they have been filtered

    for (var i = groupsOfFilters.length - 1; i >= 0; i--) {
        selectedPlayers = this.getIndividuals(selectionPool = selectionPool, filters = groupsOfFilters[i]);
        for (var j = selectedPlayers.length - 1; j >= 0; j--) {
            if ($.inArray(selectedPlayers[j]) > -1) {
                groupList.push(selectedPlayers[j]);
            }
        }
    }

    if (typeof expectedCount !== "undefined") {
        if (expectedCount !== groupList.length) {
            throw "Expected group size (" + String(expectedCount) + ") doesn't match the amount that was retrieved by the filters (" + String(groupList.length) + ").";
        }
        else if (expectedCount === 1) {
            return groupList[0];            // if you know you're expecting one, return it
        }
    }

    return groupList;
}

// might need a dict to enforce which selection it should be
Game.prototype.getIndividuals = function (selectionPool, filters, expectedCount) {
    if (typeof selectionPool === "undefined") {
        selectionPool = this.players;
    }
    /*******************************************************************************************************************
    * Loop through player list and apply all filters
    *******************************************************************************************************************/
    groupList = selectionPool;
    for (var i = filters.length - 1; i >= 0; i--) {
        if (groupList.length === 0) {
            return groupList;   // if no results turn up after the first filter is applied, give up immediately
        }

        var filteredGroup = []; // variable used to temporarily store players that match the current filter

                                                            /***********************************************************
                                                            * Filter based on player.state
                                                            ***********************************************************/
        if ($.inArray(filters[i], ["alive", "dead", "dying"]) > -1) {
            filteredGroup = [];
            for (var j = groupList.length - 1; j >= 0; j--) {
                if (groupList[j].state === filters[i]) {
                    filteredGroup.push(groupList[j])
                }
            }
            groupList = filteredGroup;
        }
                                                            /***********************************************************
                                                            * Filter based on last event unnecessary for JS?
                                                            ***********************************************************/

                                                            /***********************************************************
                                                            * Filter based on player.character
                                                            ***********************************************************/
        if ($.inArray(filters[i], ["werewolf", "human", "witch", "mystic"]) > -1){
            filteredGroup = [];
            for (var j = groupList.length - 1; j >= 0; j--) {
                if (groupList[j].character === filters[i]){
                    filteredGroup.push(groupList[j]);
                }
            }
            groupList = filteredGroup;
        }
                                                            /***********************************************************
                                                            * Filter based on p_id (regex)
                                                            ***********************************************************/
        if (/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(filters[i])){
            filteredGroup = [];
            for (var j = groupList.length - 1; j >= 0; j--){
                if (groupList[j].p_id === filters[i]){
                    filteredGroup.push(groupList[j]);
                }
            }
            groupList = filteredGroup;
        }
    }
    return groupList;
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

    $("#event_list").html("");
    for (var event of this.event_queue) {
        console.log(event);
        event.display();
    }
    for (var event of this.event_history) {
        console.log(event);
        event.display();
    }
}