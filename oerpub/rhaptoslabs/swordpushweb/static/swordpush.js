
function showWaitMessage(slideSpeed) {
    $('#upload-wait').center();
    if ( typeof slideSpeed !== 'undefined' ) {
        $('#upload-wait').slideDown(slideSpeed);
    }
    else {
        $('#upload-wait').slideDown();
    }
}

var em_cookie = 'oerpushweb.expertmode';
var selected_row = null;

$(document).ready(function()
{
    // A friendly message confirming that the upload is happening.
    // Max: added #url-submit and .forward-button (metadata page) too
    $('#file-submit, #url-submit, #presentation-submit, #metadata .forward-button').click(function(e) {
        showWaitMessage('slow');
    });

    // Toggle advanced mode explanation on hover
    $("#expertmode").mouseover(function(){
      if ($("#advanced-message").css("display") == 'none') {
        $("#basic-message").show();
        $(this).addClass("expert-activated");
      }
    }).mouseout(function(){
      if ($("#advanced-message").css("display") == 'none') {
        $("#basic-message").hide();
        $(this).removeClass("expert-activated");
      }
    });

    // Display advanced mode notice on click
    $("#expertmode").toggle(function(){
      $("#advanced-message").show();
      $("#basic-message").hide();
      $(this).addClass("expert-activated");
      $(".advanced").show();
      $(".advanced2").show();
      $(".non-advanced").hide();
      $("#expand-advanced").hide();
    }, function(){
      $("#advanced-message").hide();
      $("#expand-advanced").show();
      $(this).removeClass("expert-activated");
      $(".advanced").hide();
      $(".advanced2").hide();
      $(".non-advanced").show();
    });

    // Display advanced mode notice on click
    $("#expertmode").toggle(enableExpertMode, disableExpertMode);

    
  // Reveal error message ("Failure" page)
  $("#see-error").click(function(){
    if ($("#error_message").css('display') == 'none') {
      $("#error_message").show();
      $("#see-error input").attr('checked', true);
    } else {
      $("#error_message").hide();
      $("#see-error input").attr('checked', false);
    }
  });

    // Simple file upload
    $('input#file-submit').click(function(event){
        event.preventDefault();
        $('input#upload_file').click();
    });
    
    $('input#presentation-submit').click(function(event){
        event.preventDefault();
        $('input#importer').click();
    });

    $('input#upload_file').change(function(event){
        showWaitMessage();
        $('form#officedocument_form').submit(); 
    });

    $('input#importer').change(function(event){
        showWaitMessage();
        $('form#presentationform').submit(); 
    });
    $('input#url-submit').click(function(event){
        showWaitMessage();
    });

    $('input#choose-importer').click(function(event){
        if ($('#import-to-google').is(':checked')) {
            $('input#upload-to-google').val("true");
        
        } 
        if ($('#import-to-ss').is(':checked')) {
            $('input#upload-to-ss').val("true");
        }  
    });

    // Show the "New or existing module?" overlay.
    $('#show-neworexisting').click(function(e) {
        if(!e.isDefaultPrevented()){
            //$('#neworexisting').modal();
        }
        e.preventDefault();
    });

	$('#options-submit').click(function(e){
		$('form#optionsform').submit(); 
	});
    // Hide the "New or existing module?" overlay.
    $('#cancel-neworexisting').click(function(e) {
        e.preventDefault();
        $.modal.close();
    });

    // Apply the "New or existing module?" overlay.
    $('.submit-neworexisting').click(function(e) {
        e.preventDefault();
        url = $(this).attr('url');
        $.modal.close();
        window.location = url;
    });

    // Workgroup menu ("Describe your module" and "Choose module" pages) derived
    // from Aaron Miller's work at:
    //   http://www.awmcreative.com/blog/jquery/jquery-pop-menu/ 
    $("a.popMenu").click(function(event){
      var popOut = $(this).closest("ul.popMenu").find("ul.popOut");
      var popMenuLi = $(this).closest("ul.popMenu").children("li");
      if (popOut.css("display") == 'none') {
        popOut.show();
        popMenuLi.addClass("hover");
      } else {
        popOut.hide();
        popMenuLi.removeClass("hover");
      }
      return false;
    });

    $("ul.popOut li").click(function(event){
      var popOut = $(this).closest("ul.popMenu").find("ul.popOut");
      var popMenuLi = $(this).closest("ul.popMenu").children("li");
      popOut.hide();
      popMenuLi.removeClass("hover");
    });

    // Show the chosen workgroup as selected when it's been clicked
    $(".popOut li").has("a").click(function(e){
      e.preventDefault();
      var popMenu = $(this).closest("li.popMenu");
      element = $(this).find("a");
      $('input#workspace').attr('value', $(element).attr('href'));
      popMenu.find(".workarea-choice").text($(element).text());
      popMenu.find("ul.popOut").hide();
      popMenu.removeClass("hover");
    });

    // "Finish: Upload" button ("Describe your module" page)
    $("#metadata .forward-button").click(function(){
      $('.forward-button').attr('disabled','disabled');
      $('.forward-button').val('Uploading to Connexions ...');
      $('#back-steps .button').attr('disabled','disabled');
    });

    $('input#google-submit').click(function(e) {
        e.preventDefault();
        return newPicker();
    });

    // To reveal the "Not finding your module?" link
    $("#not-finding-link").toggle(function(){
        $("#not-finding").show();
    }, function(){
        $("#not-finding").hide();
    });

    // Row highlighting for the table containing workarea contents
    $("#workarea-contents tbody tr").hover(highlightOn, highlightOff);

    // In table containing workarea contents, allow a user to select anywhere
    // in the row in order to select the associated radio button.
    // Unless they're just cliking on the little icon that links to the module.
    // Also set that row's background color to be highlighted.
    $("#workarea-contents tbody tr").click(selectModuleRow);
    
    $('div#workspace-list a.workspace-link').click(onWorkspaceChange);
});

///////////////////////////////////
// Max's .resize() javascript here:
///////////////////////////////////

$(window).resize(function(){               

    var winh = $(window).height();
    var headerh = $("#header-container").outerHeight();
    var wfnh = $("#workflownav-wrap").outerHeight();
    var eh = $("#errors-wrap").outerHeight();
    var contentp = parseInt($("#content").css("paddingTop"));
    var contentp = contentp + parseInt($("#content").css("paddingBottom"));
    var phwh = $("#pageheader-wrap").outerHeight();
    var ma = $("#module-actions .advanced").outerWidth();

    // Make the iframe fit exactly inside the remaining space
    $("iframe.fitted").height(winh - headerh - wfnh - contentp - phwh + 5);
    $("iframe.fitted").width($(window).width() - 53);
    $("iframe.fitted").contents().find('body').addClass('preview');

    /* Give the page's header the correct top margin (since the elements above
       it are in a fixed position)
       */
    $("#content").css({'margin-top': headerh + wfnh + eh})

  // Truncate the title if it gets too long
  if ($("iframe").length != 0) {
    $("#page-title").css({'white-space': 'nowrap', 'max-width': $(window).width() - ma - 100});
  }

});

// Google Picker API for the Google Docs import
function newPicker() {
google.load('picker', '1', {"callback" : createPicker});
}       

// Create and render a Picker object for selecting documents
function createPicker() {
var picker = new google.picker.PickerBuilder().
    addView(google.picker.ViewId.DOCUMENTS).
    setCallback(pickerCallback).
    build();
picker.setVisible(true);
}

// A simple callback implementation for Picker.
function pickerCallback(data) {
    if(data.action == google.picker.Action.PICKED){
        document.getElementById('gdocs_resource_id').value = google.picker.ResourceId.generate(data.docs[0]);
        document.getElementById('gdocs_access_token').value = data.docs[0].accessToken;
        showWaitMessage();
        $('form#googledocs_form').submit(); 
    }
}

function keyDown(event) {
    if ($(event.target).val() != '') {
        $('#url-submit').removeAttr('disabled');
    }
    if (event.keyCode == 13) {
        showWaitMessage();
        $('#url-submit').removeAttr('disabled');
        $('#url-submit').click();
    }
}

/* this submits the hidden login form to cnx. */
function submitloginform(event) {
    document.getElementById('submit').click();
}

// Max: added this for the swooshy wait message
jQuery.fn.center = function () {
    this.css("position","fixed");
    this.css("top", $("#content h1").offset().top + "px");
    this.css("left", (($(window).width() - this.outerWidth()) / 2) + $(window).scrollLeft() + "px");
    return this;
}

/* Update cookie depends on the javascript 'cookie.js' in the static folder
 * sibling to this file. */
function updateCookie(expertmode) {
    $.cookie(em_cookie, expertmode, { path: '/'});
}

function enableExpertMode(element) {
    updateCookie(true);
    $("#advanced-message").show();
    $("#basic-message").hide();
    $(element).addClass("expert-activated");
    $(".advanced").show();
}

function disableExpertMode(element){
     updateCookie(false);
     $("#advanced-message").hide();
     $(element).removeClass("expert-activated");
     $(".advanced").hide();
}

function selectModuleRow(event) {
    // In table containing workarea contents, allow a user to select anywhere
    // in the row in order to select the associated radio button.
    // Unless they're just cliking on the little icon that links to the module.
    // Also set that row's background color to be highlighted.
    if( !$(event.target).is(".review-module-link, .review-module-link *") ) {
        $(this).find("input[type='radio']").attr("checked","checked");
        $("#workarea-contents tbody tr").removeClass("selected-row");
        $(this).addClass("selected-row");
        module = $(this).find("input").val();
        $("input#module").attr("value", module);
        $("#workspace").attr("value", $("a#selected_workspace").attr('href'));
        $(".forward-button").removeAttr("disabled");
    }
}

function highlightOn(event) {
    $(this).addClass('hovered-row');
}

function highlightOff(event) {
    $(this).removeClass('hovered-row');
}

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

//
//  The code below might be dead ...
//

$(document).ready(function()
{
    // Slide in the service document picker on the login page.
    $('#pick-sd').click(function(e) {
        e.preventDefault();
        $('#login-line').slideUp('slow');
        $('#sd-picker').slideDown('slow');
    });

    // Return to the default service document url if cancelled.
    $('#sd-cancel').click(function(e) {
        e.preventDefault();
        $('#service_document_url').val($('#service_document_url').attr('default_val'));
        $('#sd-picker').slideUp('slow');
        $('#login-line').slideDown('slow');
    });

    // BNW; can not grok the precondition for title truncation
    // BNW: don't think below code ever truncates title
    // Truncate the title if it gets too long
    var ma = $("#module-actions .advanced").outerWidth();
    if ($("iframe").length != 0) {
      $("#page-title").css({'white-space': 'nowrap', 'max-width': $(window).width() - ma - 100});
    }

});
