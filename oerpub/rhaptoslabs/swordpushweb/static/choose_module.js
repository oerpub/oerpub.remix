function onWorkspaceChange(event) {
    event.preventDefault();
    showWaitMessage();

    var workspace_url = $(this).attr('href');
    $.ajax({
        url: 'modules_list',
        cache: false,
        dataType: 'html',
        data: {'workspace': workspace_url},
        success: updateModules,
        error: showError,
    });
}

function updateModules(data, textStatus, jqXHR) {
    $('.forward-button').attr('disabled','disabled');

    html = $(data);
    $('div#modules-list').replaceWith(html);

    $("#workarea-contents tbody tr").hover(highlightOn, highlightOff);
    $("#workarea-contents tbody tr").click(selectModuleRow);
    $('div#workspace-list a.workspace-link').click(onWorkspaceChange);
    $('#upload-wait').slideUp('slow');
}

function showError(jqXHR, textStatus, errorThrown) {
    alert(textStatus);
}

$(document).ready(function()
{
    $('div#workspace-list a.workspace-link').click(onWorkspaceChange);
});
