/***********************************************************************************************************************
*                File : swampdragon_init.js
*              Author : Richard Webb
*                Date : 28/06/2016
*   Short description : Performs the default initialisation of swampdragon for the app
*    Full description : Subscribes to channels, calls initiating router and establishes event handlers
*                       Primarily used as a place for adding ad-hoc developer buttons.
*
* ----------------------------------------------------------------------------------------------------------------------
* Version     Date          Author              Description
* ----------------------------------------------------------------------------------------------------------------------
* 1.0         28/06/2016    Richard Webb        Initial version
*
***********************************************************************************************************************/

swampdragon.ready(function () {
    swampdragon.subscribe('lobby', 'default', { 'session_key': session_key }, null, null);
    console.log("subscribed");

    swampdragon.callRouter('init', 'lobby', { 'session_key': session_key }, function (context, data) {
        console.log("message pushed locally: " + data);
    });

    $("#quick_match").on('click', function () {
        swampdragon.callRouter('matchmaking', 'lobby', { 'session_key': $('#sessionID').html(), 'action': 'join_game' }, function (context, data) {
            swampdragon.subscribe('lobby', 'misc', { 'session_key': $('#sessionID').html() }, null, null);
            console.log(data);
            $('#server_updates').prepend("<span class='message'>" + data.text + ": " + data.g_id + "</span>");
        });
    });

    $("#leave_match").on('click', function () {
        // call popup with parameters to fill out
        var parameters = { 'session_key': $('#sessionID').html(), 'action': 'leave_game' };
        swampdragon.callRouter('matchmaking', 'lobby', parameters, function (context, data) {
            var parameters = {
                'session_key': $('#sessionID').html(),
                'action': 'unsubscribe',
                'listener': 'game'
            };
            swampdragon.unsubscribe('lobby', 'game', parameters, function (context, data) {
                console.log("unsubscription from game messages complete");
                console.log(data);
                $('#server_updates').prepend("<span class='message'>" + data + "</span>");
            });
        });
    });

    $("#flush_db").on('click', function () {
        // call popup with parameters to fill out
        var parameters = { 'session_key': $('#sessionID').html(), 'action': 'flush_db' };
        swampdragon.callRouter('matchmaking', 'lobby', parameters, function (context, data) {
            console.log(data);
            $('#server_updates').prepend("<span class='message'>" + data + "</span>");
        });
    });
    $("#broadcast_games").on('click', function () {
        // call popup with parameters to fill out
        var parameters = {};
        swampdragon.callRouter('broadcast_games', 'lobby', parameters, function (context, data) { });
    });
    $("#add_vote").on('click', function () {
        // call popup with parameters to fill out
        var myVote = prompt("enter p_id", "xxx-xxx-xxx");
        var parameters = { 'vote': myVote };
        if (parameters.vote != '')
            swampdragon.callRouter('vote', 'lobby', parameters, function (context, data) { });
    });
    $("#test_game").on("click", function () {
        var player_count = prompt("enter number of players (this should match the server side hardcoded limit)", 4);
        var parameters = {};
        parameters['session_key'] = session_key;
        parameters['player_count'] = player_count;
        parameters['action'] = "test_game";
        swampdragon.callRouter('developer', 'lobby', parameters, function (context, data) { alert("done"); });
    });
    $("#ask_update").on("click", function () {
        var parameters = {};
        parameters['session_key'] = session_key;
        parameters['action'] = "ask_update";
        swampdragon.callRouter('developer', 'lobby', parameters, function (context, data) { console.log(data); });
    });
    $("#gain_info").on("click", function () {
        var parameters = {};
        parameters['attribute_filter'] = prompt("enter comma separated attributes to gain info on player 2 in the session's game", "state");
        parameters['session_key'] = session_key;
        parameters['action'] = "gain_info";
        swampdragon.callRouter('developer', 'lobby', parameters, function (context, data) { console.log(data); });
    });
    $("#lose_info").on("click", function () {
        var parameters = {};
        parameters['attribute_filter'] = prompt("enter comma separated attributes to gain info on player 2 in the session's game", "state");
        parameters['session_key'] = session_key;
        parameters['action'] = "lose_info";
        swampdragon.callRouter('developer', 'lobby', parameters, function (context, data) { console.log(data); });
    });
});