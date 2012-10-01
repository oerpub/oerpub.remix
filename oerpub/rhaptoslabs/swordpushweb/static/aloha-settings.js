(function(window, undefined){

    if (window.Aloha === undefined || window.Aloha === null) {
        var Aloha = window.Aloha = {};
    }

    Aloha.settings = {
        jQuery: window.jQuery,
        logLevels: {'error': true, 'warn': true, 'info': false, 'debug': false},
        errorhandling : true,

        plugins: {
            block: {
                defaults : {
                    '.default-block': {
                    },
                    'figure': {
                        'aloha-block-type': 'EditableImageBlock'
                    },
                },
                rootTags: ['span', 'div', 'table', 'figure']
            }
        },
        bundles: {
            // Path for custom bundle relative from require.js path
            user: '../demo/block'
        }
    };
})(window);
