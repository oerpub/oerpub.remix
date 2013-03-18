Aloha.ready(function(){
    Aloha.require(['PubSub'], function(PubSub){
        // Subscribe to the 'swordpushweb.save' event.
        // It is fired by the the AlohaEditor when someone clicks
        // the 'Save' button.
        // Disable the navigation buttons.
        PubSub.sub('swordpushweb.saving', function(data) {
            $('#statusmessage').data('message')('Saving...');
            $('#btn-back').attr('disabled', 'disabled');
            $('#btn-forward').attr('disabled', 'disabled');
        });

        // subscribe to the 'swordpusweb.saved' event. It is fired
        // by the 'savePreview' function in the AlohaEditor.oerpub
        // index.html page.
        // Here we re-enable the navigation buttons.
        PubSub.sub('swordpushweb.saved', function(data) {
            $('#btn-back').removeAttr('disabled');
            $('#btn-forward').removeAttr('disabled');

            $('#upload-wait').slideUp('slow');
        });

        $('#btn-forward').click(function(e) {
            var editor = Aloha.getEditableById('canvas');
            editor.savePreview();
            return true;
        });
    });
});
