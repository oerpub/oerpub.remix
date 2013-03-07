// JavaScript for the choose page template


$(document).ready(function()
{
    $('input#presentation-submit').click(function(event){
        event.preventDefault();
        $('input#importer').click();
    });
});
