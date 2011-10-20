$(document).ready(function()
{

    $('#pick-sd').click(function(e) {
        e.preventDefault();
        $('#login-line').slideUp('slow');
        $('#sd-picker').slideDown('slow');
    });

    $('#upload-submit').click(function(e) {
        $('#upload-wait').slideDown('slow');
    });

    $('#sd-cancel').click(function(e) {
        e.preventDefault();
        $('#service_document_url').val($('#service_document_url').attr('default_val'));
        $('#sd-picker').slideUp('slow');
        $('#login-line').slideDown('slow');
    });
});
