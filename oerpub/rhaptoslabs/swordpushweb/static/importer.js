// JavaScript for the slide importer page template


$(document).ready(function()
{
    $('input#choose-importer').click(function(event){
        if ($('#import-to-google').is(':checked')) {
            $('input#upload-to-google').val("true");
        
        } 
        if ($('#import-to-ss').is(':checked')) {
            $('input#upload-to-ss').val("true");
        }  
    });

});
