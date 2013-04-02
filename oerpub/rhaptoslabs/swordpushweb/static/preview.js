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
	        // make sure that the document is saved before
	        // leaving the page
                var promise = saveEditableArea();
                $.when(promise).done(function() {
                    // alert('promised fulfilled!!!');
                    // delayed propagation of event ... wait until the editable is saved
                    $('#btn-forward').click();
                });
                event.stopPropagation();
                event.preventDefault();
            } else {
                // clicking #btn-forward will pop a bootstrap dbox
                // asking whether to upload to a new or existing module.
                // there are two workflows where this is not necessary
                // since the new or existing decision has already been made.
                source = $('#source').attr('value');
                if ( source === 'new' || source === 'existingmodule' ) {
                    event.stopPropagation();
                    event.preventDefault();
                    window.location = '/metadata';
                    return false;
                }
                return true;
            }
        });

        $('#download-copy').click(function(event) {
            if (Aloha.getEditableById('canvas').isModified()) {
                var promise = saveEditableArea();
                $.when(promise).done(function() {
                    //alert('promised fulfilled!!!');
                    // delayed propagation of event ... wait until the editable is saved
                    var href = $('#download-copy').attr('href');
                    window.location = href;
                });
                event.stopPropagation();
                event.preventDefault();
            } else {
                return true;
            }
        });

        $('#edit-xml').click(function(event) {
            if (Aloha.getEditableById('canvas').isModified()) {
                var promise = saveEditableArea();
                $.when(promise).done(function() {
                    //alert('promised fulfilled!!!');
                    // delayed propagation of event ... wait until the editable is saved
                    var href = $('#edit-xml').attr('href');
                    window.location = href;
                });
                event.stopPropagation();
                event.preventDefault();
            } else {
                return true;
            }
        });

        $('#neworexisting').on('hidden', function() {
            $('#upload-wait').slideUp('slow');

            var btn = $('#btn-newmodule');
            $(btn).removeAttr('disabled');
            $(btn).addClass('btn-primary');
           
            var btn = $('#btn-exsitingmodule');
            $(btn).removeAttr('disabled');
            $(btn).addClass('btn-primary');
        });

        // subscribe to the 'swordpusweb.saved' event. It is fired
        // by the 'savePreview' function in the AlohaEditor.oerpub
        // index.html page.
        // Here we re-enable the navigation buttons.
        PubSub.sub('swordpushweb.saved', function(data) {
            var btn = $('#back-to-chooser');
            btn.removeAttr('disabled');

            var btn = $('#show-neworexisting');
            btn.removeAttr('disabled');

            var btn = $('#btn-newmodule');
            btn.removeAttr('disabled');
            btn.addClass('btn-primary');
            
            var btn = $('#btn-existingmodule');
            btn.removeAttr('disabled');
            btn.addClass('btn-primary');

            $('#upload-wait').slideUp('slow');
        });

        $('#btn-existingmodule').click(function(evt) {
            $.ajax({
              dataType: "json",
              type: 'POST',
              async: false,
              url: '/json_set_target_on_session',
              data: {target: 'existingmodule'},
              success: function(data) {
                //alert(data);
              },
              fail: function(data) {
                //alert(data);
              },
              error: function(data) {
                //alert(data);
              }
            });
            evt.stopPropagation();
        });

    });
});

//Aloha.bind('aloha-editable-activated', function($event, activateObj) {
Aloha.bind('aloha-selection-changed', function($event, rangeObject) {
    // not getting the activate event for the title editable area
    // until focus is placed there (tcket 308)
    // we do get a selection change event, so that's have we'll roll
    var $start; 
    var editable; 
    $start = $(rangeObject.startContainer);
    // this did not work as advertised ... could be something deeply wrong with our title editable area
    // editable = Aloha.getEditableHost($start);
    if ( !$start.is('.title-editor') ) {
      $start = $start.parents('.title-editor');
    }
    if ( $start.is('.title-editor') ) {
      var $title = $start;
      var title = $title.text();
      if ( title == 'Enter title here' ) {
        var range;
        range = new GENTICS.Utils.RangeObject();;
        range.startContainer = range.endContainer = $title.get(0);
        range.startOffset = 0;
        range.endOffset = 1;
        range.select();
       }
    }
});
