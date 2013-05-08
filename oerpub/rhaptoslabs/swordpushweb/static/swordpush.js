
// Max: added this for the swooshy wait message
jQuery.fn.center = function () {
    this.css("position","fixed");
    this.css("top", $("#content h1").offset().top + "px");
    this.css("left", (($(window).width() - this.outerWidth()) / 2) + $(window).scrollLeft() + "px");
    return this;
}

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
    // FIXME: This way of using toggle() is deprecated in Jquery 1.7
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
    
    $('input#url-submit').click(function(event){
        showWaitMessage();
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
      // update the workspace form value
      $('input#workspace').attr('value', $(element).attr('href'));
      // update the displayed workspace selection
      popMenu.find("#selected_workspace").attr('href', $(element).attr('href'));
      popMenu.find(".workarea-choice").text($(element).text());
      popMenu.find("ul.popOut").hide();
      popMenu.removeClass("hover");
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

    // Fade the flash message
    $('#flashmessages').delay(5000).fadeOut(1000);
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
        $(".forward-button").removeAttr("disabled");
    }
}

function highlightOn(event) {
    $(this).addClass('hovered-row');
}

function highlightOff(event) {
    $(this).removeClass('hovered-row');
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
