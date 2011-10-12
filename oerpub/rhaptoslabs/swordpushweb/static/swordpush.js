$(document).ready(function()
{
    $('#workspace-changer').change(function() {
        $.post('/change_workspace', $('#workspace-form').serialize());
    });
});
