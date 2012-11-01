(function(window, undefined){

    if (window.Aloha === undefined || window.Aloha === null) {
        var Aloha = window.Aloha = {};
    }

    Aloha.settings = {
        jQuery: window.jQuery,
        logLevels: {'error': true, 'warn': true, 'info': false, 'debug': false},
        errorhandling : true,
        waitSeconds: 0,
        plugins: {
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
                uploadurl: '/upload_dnd',
                uploadmethod: 'POST',
                uploadfield: 'upload'
            }
        },
        bundles: {
            // Path for custom bundle relative from require.js path
            oerpub: '../plugins/oerpub'
        }
    };
})(window);
