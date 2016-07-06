/***********************************************************************************************************************
* User methods
***********************************************************************************************************************/
function User(userJson) {
    if (typeof (userJson) === "string") {
        userJson = JSON.parse(userJson)
    }
    this.location = userJson.location;
    this.p_id = userJson.p_id;
    if ('g_id' in userJson) {
        this.g_id = userJson.g_id;    // unnecessary/unused?
    }
    else {
        this.g_id = null;
    }
}