(function(window, undefined){

    if (window.Aloha === undefined || window.Aloha === null) {
        var Aloha = window.Aloha = {};
    }

    require.config({ waitSeconds: 42 });

    Aloha.settings = {
        jQuery: window.jQuery,
        logLevels: {'error': true, 'warn': true, 'info': false, 'debug': false},
        errorhandling : true,
        requireConfig: {
            waitSeconds: 42,
            paths: {
                // Override location of jquery-ui and use our own. Because
                // jquery-ui and bootstrap conflict in a few cases (buttons,
                // tooltip) our copy has those removed.
                jqueryui: '../../oerpub/js/jquery-ui-1.9.0.custom-aloha'
            }
        },
        plugins: {
            assorted: {
                image: {
                    preview: true,
                    uploadurl: '/upload_dnd'
                }
            },
            genericbutton: {
                buttons: [{'id': 'save', 'title': 'Save', 'event': 'swordpushweb.save' }]
            },
            format: {
                config : ['b', 'i', 'u', 'p', 'sub', 'sup', 'h1', 'h2', 'h3']
            },
            block: {
                defaults : {
                    '.default-block': {
                    },
                    'figure': {
                        'aloha-block-type': 'FigureBlock'
                    }
                },
                rootTags: ['span', 'div', 'figure'],
                dragdrop: "1"
            },
            image: {
                onUploadSuccess: function(xhr){
                    // Expect a json-formatted response
                    try {
                        var msg = JSON.parse(xhr.response);
                        return msg.url;
                    } catch(e) {}
                    return null;
                }
            },
            draganddropfiles: {
                upload: {
                    config: {
                        url: '/upload_dnd',
                        send_multipart_form: true,
                        fieldName: 'upload'
                    }
                }
            },
            math: {
                cheatsheet: true
            }
        },
        bundles: {
            // Path for custom bundle relative from require.js path
            oer: '../plugins/oer'
        },
        contentHandler: {
            insertHtml: [ 'word', 'generic', 'oembed'],
            initEditable: [],
            getContents: []
        }
    };
})(window);
