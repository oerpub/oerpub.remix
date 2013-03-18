// Confirm if user really wants to sign out before work is uploaded
var confirmMsg1 = "Are you sure you want to sign out? \n\nYour module has not been uploaded and any work on it will be lost if you sign out now.";
var confirmMsg2 = "Are you sure you want to leave this page? \n\nYour module has not been uploaded and any work on it will be lost if you return to the beginning.";
var confirmMsg3 = "Are you sure you want to leave this page? \n\nYour changes have not been saved and any work will be lost if you leave this page.";
var confirmMsg4 = "Are you sure you want to leave this page? \n\nYour module has not been uploaded and any work on it will be lost if you leave. \n\nTo attempt the upload again, click 'Cancel' and 'Try to upload again'.";

$(document).ready(function()
{
    $("#btn-back, #start-over input").click(function(e){
        if ($("#edit-frame").length != 0 || $("#metadata").length != 0 && $(this).attr("id") == 'btn-back') {
            return _doAction(confirmMsg3, e);
        } else if ($("#see-error").length != 0) {
            return _doAction(confirmMsg4, e);
        } else if ($("iframe").length != 0 || $("#metadata").length != 0) {
            return _doAction(confirmMsg2, e);
        } else if ($("div#canvas").length != 0) {
            return _doAction(confirmMsg3, e);
        } else {
            return true;
        }
    });

    $("a#logout_link").click(function(event){
        if ($("iframe.fitted").length != 0 || $("#metadata").length != 0) {
            return _doAction(confirmMsg1, event);
        }
    });
    
    $("#choose-new-document, #back-to-preview").click(function(e){
        return _doAction(confirmMsg3, e);
    });


    $('a#cnxlogo_link, img.cnxlogo, #header h1 a').click(function(e) {
        return _doAction(confirmMsg2, e);
    });

    ///////////////////////////////////////////////////////////////////////////
    // Not sure this is still used. Validate and delete if unused.
    ///////////////////////////////////////////////////////////////////////////
    $("#status a").click(function(event){
        if ($("#edit-frame").length != 0) {
            return _doAction(confirmMsg3, event);
        } else if ($("#see-error").length != 0) {
            return _doAction(confirmMsg4, event);
        }
        return true;
    });
    ///////////////////////////////////////////////////////////////////////////

});

function _doAction(message, event) {
    // don't let the event propagate up, we handle all actions here.
    // challenge the user before doing the action.
    var element = event.target;
    var c = confirm(message);
    if (c == true) { 
        return true;
    } else {
        event.preventDefault(); 
        event.stopPropagation();
        return false;
    }
}

function _doNavAction(event) {
    var element = event.target;
    var target = $(element).attr('href');
    if (!target) {
        target = $(element).attr('url');
    }
    window.location = target;
    event.stopPropagation();
    return true;
}
