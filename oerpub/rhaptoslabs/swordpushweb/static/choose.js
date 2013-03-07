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
