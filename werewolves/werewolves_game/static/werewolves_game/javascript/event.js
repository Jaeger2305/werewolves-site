/***********************************************************************************************************************
* Event methods
***********************************************************************************************************************/
function Event(jsonEvent, parentGame) {
    if (typeof (jsonEvent) === "string")     // fails if string created as object, better than nothing
        newEvent = JSON.parse(jsonEvent);
    else {
        newEvent = jsonEvent      // more appropriate naming
    }
    this.parentGame = parentGame

    this.e_id = newEvent.e_id;
                                                            /***********************************************************
                                                            * Create player objects as they were at the latest update of
                                                            * this event
                                                            ***********************************************************/
    this.subjects = [];
    for (var playerJson in newEvent.subjects) {
        this.subjects.push(new Player(newEvent.subjects[playerJson]));
    }

    this.instigators = [];
    for (var playerJson in newEvent.instigators) {
        this.instigators.push(new Player(newEvent.instigators[playerJson]));
    }

    this.result_subjects = [];
    for (var playerJson in newEvent.result_subjects) {
        this.result_subjects.push(new Player(newEvent.result_subjects[playerJson]));
    }

    this.votes = newEvent.votes;       // this needs updating. Could be a separate object tying votes against subjects
}

Event.prototype.update = function (jsonEvent) {
    if (typeof (jsonEvent) === "string")     // fails if string created as object, better than nothing
        updatedEvent = JSON.parse(jsonEvent);
    else {
        updatedEvent = jsonEvent      // more appropriate naming
    }
    if ('e_id' in updatedEvent) { this.e_id = updatedEvent.e_id; }
    if ('e_type' in updatedEvent) { this.e_type = updatedEvent.e_type; }

    if ('subjects' in updatedEvent) {
        this.subjects = [];
        for (var playerJson in updatedEvent.subjects) {
            this.subjects.push(new Player(updatedEvent.subjects[playerJson]));
        }
    }

    if ('instigators' in updatedEvent) {
        this.instigators = [];
        for (var playerJson in updatedEvent.instigators) {
            this.instigators.push(new Player(updatedEvent.instigators[playerJson]));
        }
    }

    if ('result_subjects' in updatedEvent) {
        this.result_subjects = [];
        for (var playerJson in updatedEvent.result_subjects) {
            this.result_subjects.push(new Player(updatedEvent.result_subjects[playerJson]));
        }
    }

    if ('votes' in updatedEvent) { this.votes = updatedEvent.votes; }
}

// returns the player object at the time it was snapshot in the event, with updated attribtues
// UNTESTED!
Event.prototype.updateSnapshotPlayer = function (playerOld, playerNew, attributes){
    var updatedSnapshotPlayer = $.extend(true, {}, playerOld);
    for (attribute in playerNew) {
        if (attribute in attributes) {
            updatedSnapshotPlayer[attribute] = playerNew[attribute];
        }
    }
    return;
}

Event.prototype.display = function () {
    $("#event_list").append(
        "<tr>" +
            "<td>e_id</td>" +
            "<td>e_type</td>" +
            "<td>subjects</td>" +
            "<td>instigators</td>" +
            "<td>result_subjects</td>" +
            "<td>votes</td>" +
        "</tr>" +
        "<tr>" +
            "<td>" + this.e_id + "</td>" +
            "<td>" + this.e_type + "</td>" +
            "<td>" + this.subjects + "</td>" +
            "<td>" + this.instigators + "</td>" +
            "<td>" + this.result_subjects + "</td>" +
            "<td>" + this.votes + "</td>" +
        "</tr>"
    );
}