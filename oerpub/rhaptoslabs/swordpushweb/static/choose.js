// JavaScript for the choose page template


$(document).ready(function()
{
    $('input#presentation-submit').click(function(event){
        event.preventDefault();
        $('input#importer').click();
    });

    $('input#upload_file').change(function(event){
        showWaitMessage();
        $('form#officedocument_form').submit(); 
    });

    $('input#importer').change(function(event){
        showWaitMessage();
        $('form#presentationform').submit(); 
    });

});

//
// Google Picker API for the Google Docs import
//

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

// A simple callback implementation for Picker.
function pickerCallback(data) {
    if(data.action == google.picker.Action.PICKED){
        document.getElementById('gdocs_resource_id').value = google.picker.ResourceId.generate(data.docs[0]);
        document.getElementById('gdocs_access_token').value = data.docs[0].accessToken;
        showWaitMessage();
        $('form#googledocs_form').submit(); 
    }
}

$(document).ready(function()
{
    $('input#google-submit').click(function(e) {
        e.preventDefault();
        return newPicker();
    });

});
