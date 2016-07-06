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
    if ('character' in playerJson) { this.character = playerJson.character; }
}


                                                            /***********************************************************
                                                            * Message methods
                                                            ***********************************************************/
Player.prototype.message = function (msg, targetPID) {
    parameters = { "msg": msg, "target": targetPID, "session_key": session_key };
    swampdragon.callRouter('messaging', 'lobby', parameters, function (context, data) {
        console.log(data);
        $('#server_updates').prepend("<div class='message'>" + data + "</div>");
    });
}

Player.prototype.receive_message = function (msg, sender, target, time) {
    var constructed = "";
    constructed = "<div class=message_target_" + target + ">[" + time + "] " + sender + ": " + msg + "</div>";
    $("#chatbox_read").append(constructed);
}