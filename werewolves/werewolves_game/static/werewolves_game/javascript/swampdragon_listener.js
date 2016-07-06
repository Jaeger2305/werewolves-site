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
        var broadcastGames = [];
        for (stringGame in message.data.games) {
            var jsonGame = JSON.parse(message.data.games[stringGame]);
            console.log("jsonGame:");
            console.log(jsonGame);
            existingGame = gameManager.find(jsonGame.g_id);
            if (existingGame) {
                existingGame.update(jsonGame);
                broadcastGames.push(existingGame);
            }
            else {
                var newGame = new Game(jsonGame);
                gameManager.add_game(newGame);
                broadcastGames.push(newGame);
            }
        }
    // remove games that don't exist in the broadcast
        for (var i = gameManager.gameList.length - 1; i >= 0; i--) {
            if ($.inArray(gameManager.gameList[i], broadcastGames) === -1)
                gameManager.gameList.splice(i, 1);
        }
        gameManager.display();
    }
    if (message.data.type == "message") {
        myPlayer.receive_message(message.data.message, message.data.sender, message.data.target, message.data.time);
    }

    console.log(message.data.channel);
});