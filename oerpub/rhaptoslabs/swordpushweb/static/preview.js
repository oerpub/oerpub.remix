Aloha.ready(function(){
    Aloha.require(['PubSub'], function(PubSub){
        // Subscribe to the 'swordpushweb.save' event.
        // It is fired by the the AlohaEditor when someone clicks
        // the 'Save' button.
        // Disable the navigation buttons.
        PubSub.sub('swordpushweb.save', function(data) {
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

        function saveEditableArea() {
            var deferred = $.Deferred();
            var subscriptionId;
            PubSub.pub('swordpushweb.save');
            subscriptionId = PubSub.sub('swordpushweb.saved', function() {
                deferred.resolve();
                PubSub.unsub(subscriptionId);
            });
            return deferred.promise();
        }

        $('#btn-forward').click(function(event) {
            if (Aloha.getEditableById('canvas').isModified()) {
                var promise = saveEditableArea();
                $.when(promise).done(function() {
                    // alert('promised fulfilled!!!');
                    // delayed propagation of event ... wait until the editable is saved
                    $('#btn-forward').click();
                });
                event.stopPropagation();
                event.preventDefault();
            } else {
                return true;
            }
        });
	
    });
});
