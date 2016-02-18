/*********************************************************
*
* session.js
* Heartbeat connection to the server
*
 ***********************************************************/

function pulse_activity(callback){
	return $.ajax({
		url:  document.location.origin+"/werewolves_game/extend_session",
		type: 'get',
		data: {'session_key':$('#sessionID').html()},
		success: callback,
	});
}

function pulse_handler(){
	pulse_activity(function(data){
		//console.log("pulse_activity: "+data);
		window.setTimeout(pulse_activity, 25000);
	});
}