// JavaScript for the metadata page template


$(document).ready(function()
{
    $("#start-from-beginning").click(function(e){
        var target = $(this).attr('href');
        if (!target) {
            target = $(this).attr('url');
        }
        window.location = target;
        return true;
    });

});

