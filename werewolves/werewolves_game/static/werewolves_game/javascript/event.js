/***********************************************************************************************************************
* Event methods
***********************************************************************************************************************/
function Event(jsonEvent) {
    if (typeof (jsonEvent) === "string")     // fails if string created as object, better than nothing
        newEvent = JSON.parse(jsonEvent);
    else {
        newEvent = jsonEvent      // more appropriate naming
    }

    this.e_id = newEvent.e_id;
    this.subjects = newEvent.subjects;
    this.players = [];
    for (var playerJson in players) {
        this.players.push(new Player(players[playerJson]));
    }

    if ($.inArray(activeUser.p_id, gameJson.players)) {
        gameManager.makeActiveGame(this.g_id)
    }
}
self.subjects                   = subjects			# list of those the events affects
self.instigators                = instigators		# list of those starting the event
self.action                     = action			# function that will implement the effect
self.g_id                       = g_id
self.e_type                     = e_type
self.result_subjects            = result_subjects
self.votes                      = votes
self.voting_callback_reference  = voting_callback_reference
self.action_without_instigators = False

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

Game.prototype.display = function () {
    $("#player_list").html("");
    for (var player of this.players) {
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