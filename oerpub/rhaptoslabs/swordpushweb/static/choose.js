// JavaScript for the choose page template


function keyDown(event) {
    if ($(event.target).val() != '') {
        $('#url-submit').removeAttr('disabled');
    }
    if (event.keyCode == 13) {
        showWaitMessage();
        $('#url-submit').removeAttr('disabled');
        $('#url-submit').click();
    }
}

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

    // Zip file upload
    $('input#zip-file-submit').click(function(event) {
        // user clicks the input button to upload and edit a zip file
        // we redirect that click to a hidden file input 
        // which launches an OS specific Open File dbox 
        // which loads the value attribute of the file input 
        // on successful file upload
        event.preventDefault();
	// front end of the async file upload to client
        $('input#upload_zip_file').click();
    });

    $('#zip-file-submit').click(function(e) {
        showWaitMessage('slow');
    });

    $('input#upload_zip_file').change(function(event){
	// back end of the async file upload to client
        showWaitMessage();
        $('form#zip_or_latex_form').submit(); 
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
        $('#gdocs_resource_id').val(data.docs[0].id);
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
