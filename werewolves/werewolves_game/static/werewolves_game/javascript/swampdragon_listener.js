/***********************************************************************************************************************
*                File : swampdragon_listener.js
*              Author : Richard Webb
*                Date : 28/06/2016
*   Short description : Listens and handles messages published by the server for the channels a user is subscribed to
*    Full description : The main loop that listens to and handles the messages received from the server.
*                       These are published using the python swampdragon.pubsub_providers.data_publisher import publish_data
*                       Additionally, these messages may be returned via a router returning send.message
*
* -------------------------------------------------
* Version     Date          Author      Description
* -------------------------------------------------
* 1.0         28/06/2016    Richard Webb         Initial version
*
***********************************************************************************************************************/

swampdragon.onChannelMessage(function (channels, message) {
    if (message.data.channel === "lobbyinfo") { }
    if (message.data.channel === "sysmsg") {
        $("#server_updates").prepend("<span class='message'>" + message.data.message + "</span>");
    }
    if (message.data.channel === "player_list") {
        console.log(message.data);
    }
    if (message.data.channel.startsWith("game")) {
        // message.data.channel expected output is game:g_id
        // if game:g_id:event
        // else if game:g_id:player
        // else update all
        for (game in message.data.games) {
            var game_json = JSON.parse(message.data.games[game]);
            console.log("game_json:");
            console.log(game_json);
            javascriptGame = gameManager.find(game_json.g_id);
            if (javascriptGame)
                javascriptGame.update(game_json);
            else {
                var newGame = new Game(game_json);
                gameManager.add_game(newGame);
            }
        }
        gameManager.display();
    }
    if (message.data.type == "message") {
        myPlayer.receive_message(message.data.message, message.data.sender, message.data.target, message.data.time);
    }

    console.log(message.data.channel);
});