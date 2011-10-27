$(document).ready(function()
{

    // Slide in the service document picker on the login page.
    $('#pick-sd').click(function(e) {
        e.preventDefault();
        $('#login-line').slideUp('slow');
        $('#sd-picker').slideDown('slow');
    });

    // Return to the default service document url if cancelled.
    $('#sd-cancel').click(function(e) {
        e.preventDefault();
        $('#service_document_url').val($('#service_document_url').attr('default_val'));
        $('#sd-picker').slideUp('slow');
        $('#login-line').slideDown('slow');
    });

    // A friendly message confirming that the upload is happening.
    $('#upload-submit').click(function(e) {
        $('#upload-wait').slideDown('slow');
    });

});

// Google Picker API for the Google Docs import
function newPicker() {
google.load('picker', '1', {"callback" : createPicker});
}       

// Create and render a Picker object for selecting documents
function createPicker() {
var picker = new google.picker.PickerBuilder().
    addView(google.picker.ViewId.DOCUMENTS).
    setCallback(pickerCallback).
    build();
picker.setVisible(true);
}

// A simple callback implementation.
function pickerCallback(data) {
if(data.action == google.picker.Action.PICKED){
    document.getElementById('gdocs_resource_id').value = google.picker.ResourceId.generate(data.docs[0]);
    document.getElementById('gdocs_access_token').value = data.docs[0].accessToken;                  
    //document.getElementById('upload-submit').click();
}
}
