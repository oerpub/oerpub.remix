/* Translate between the roles form and the roles list in the sidebar. This can
 * be achieved more efficiently than here by translating into some intermediate
 * structure, but this way is more readable and debuggable. */

var roles = new Array('authors', 'maintainers', 'copyright', 'editors', 'translators');
var required_roles = new Array('authors', 'maintainers', 'copyright');
var em_cookie = 'oerpushweb.expertmode';
var selected_row = null;

/* TODO: Check that required roles are specified */

function get_user_list() {
    var userlist = new Array();
    for (var i in roles) {
       var users = $('#'+roles[i]).val().split(',');
       for (var j in users) {
           if ( $.inArray(users[j], userlist) == -1 && users[j] != '') {
               userlist.push(users[j]);
           }
       }
    }
    return userlist;
};

/* Create rows for the roles form.*/
function create_row(user_id) {
    id_list = roles.concat(["user", "remove"]);
    for (i in id_list) {
	var last_row_td = $('#roles-last-row-' + id_list[i]);
	if(last_row_td.attr("class") == "table-row-bottom")
	    last_row_td.attr("class", "table-row-general");
	last_row_td.attr("id", "");
    }
    var row = $('<tr class="roles-row" user_id="'+user_id+'">');
    if ( user_id ) {
        $('<td id="roles-last-row-user" class="table-row-bottom">').html(user_id).appendTo(row);
    } else {
        // Get a text input field to add a new role.
        $('<td id="roles-last-row-user" class="table-row-bottom">')
	    .append($('<input id="edit-new-username" type="text">').blur(fix_role_checkboxes))
	    .appendTo(row);
    };
    for (i in roles) {
        $('<td id="roles-last-row-' + roles[i] + '" class="table-row-bottom" style="text-align:center;">')
        .append($('<input type="checkbox" id="checkbox-'
                  +roles[i]+'-'+user_id+'">'))
        .appendTo(row);
    };
    $('<td id="roles-last-row-remove" style="text-align:center;">')
        .append($('<img src="static/images/delete_icon.png" alt="Delete" id="remove-'+user_id+'">').click(clear_role_checkboxes))
        .appendTo(row);
    return row;
};

/* Once the checkboxes are created, check them. */
function populate_roles_checkboxes() {
    // Populate all the roles checkboxes from the hidden fields.
    for (var i in roles) {
       var users = $('#'+roles[i]).val().split(',');
       for (var j in users) {
           $('#checkbox-'+roles[i]+'-'+users[j]).attr('checked', 'checked');
       }
    }
};

/* Get the values for the roles fields from the checkboxes */
function populate_roles_fields () {
    // Populate the fields from the roles table
    for (var i in roles) {
       var current_role = new Array();
       $('.roles-row').each(function(index) {
           user = $(this).attr('user_id');
           if ($('#checkbox-'+roles[i]+'-'+user).is(':checked')) {
               current_role.push(user);
           };
       });
       $('#'+roles[i]).val(current_role.join(','));
       $('#list-'+roles[i]+' span').html(current_role.join(', '));
    }
};

/* Clear the roles form after hiding it. */
function clear_roles_form () {
    $.modal.close();
    $('.roles-row').remove();
};

// After adding a user role, fix it and get the checkboxes sorted
function fix_role_checkboxes(e) {
    var user_id = $(this).val();
    $(this)
        .parent()
        .html(user_id)
        .parent()
        .attr('user_id', user_id);
    for (var i in roles) {
       $('#checkbox-'+roles[i]+'-')
       .attr('id', 'checkbox-'+roles[i]+'-'+user_id);
    }
    $('#remove-')
	.attr('id', 'remove-'+user_id);
};

// Clear all role checkboxes in a row
function clear_role_checkboxes(e) {
    var user_id = $(this).attr('id').substr(7);
    for (var i in roles) {
       $('#checkbox-'+roles[i]+'-'+user_id).attr('checked', false);
    }
};

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

    // A friendly message confirming that the upload is happening.
    // Max: added #url-submit and .forward-button (metadata page) too
    $('#file-submit, #url-submit, #presentation-submit, #metadata .forward-button').click(function(e) {
        $('#upload-wait').center();
        $('#upload-wait').slideDown('slow');
    });

    // Truncate the title if it gets too long
    var ma = $("#module-actions .advanced").outerWidth();
    if ($("iframe").length != 0) {
      $("#page-title").css({'white-space': 'nowrap', 'max-width': $(window).width() - ma - 100});
    }

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

    // Confirm if user really wants to sign out before work is uploaded
    var confirmMsg1 = "Are you sure you want to sign out? \n\nYour module has not been uploaded and any work on it will be lost if you sign out now.";
    var confirmMsg2 = "Are you sure you want to leave this page? \n\nYour module has not been uploaded and any work on it will be lost if you return to the beginning.";
    var confirmMsg3 = "Are you sure you want to leave this page? \n\nYour changes have not been saved and any work will be lost if you leave this page.";
    var confirmMsg4 = "Are you sure you want to leave this page? \n\nYour module has not been uploaded and any work on it will be lost if you leave. \n\nTo attempt the upload again, click 'Cancel' and 'Try to upload again'.";

    $("a#logout_link").click(function(event){
        if ($("iframe.fitted").length != 0 || $("#metadata").length != 0) {
            return _doAction(confirmMsg1, event);
        }
    });

    $("#status a").click(function(event){
        if ($("#edit-frame").length != 0) {
            return _doAction(confirmMsg3, event);
        } else if ($("#see-error").length != 0) {
            return _doAction(confirmMsg4, event);
        }
        return true;
    });

    $("#back-to-chooser, #start-over input").click(function(e){
        if ($("#edit-frame").length != 0 || $("#metadata").length != 0 && $(this).attr("id") == 'back-to-chooser') {
            return _doAction(confirmMsg3, e);
        } else if ($("#see-error").length != 0) {
            return _doAction(confirmMsg4, e);
        } else if ($("iframe").length != 0 || $("#metadata").length != 0) {
            return _doAction(confirmMsg2, e);
        } else if ($("div#canvas").length != 0) {
            return _doAction(confirmMsg3, e);
        } else {
            return true;
        }
    });

    $("#choose-new-document, #back-to-preview").click(function(e){
        return _doAction(confirmMsg3, e);
    });

    $("button#btn-navigate-back").click(function(e){
        _doNavAction(e);
    });

    $("button#btn-navigate-forward").click(function(e){
        _doNavAction(e);
    });

    $("#start-from-beginning").click(function(e){
        var target = $(this).attr('href');
        if (!target) {
            target = $(this).attr('url');
        }
        window.location = target;
        return true;
    });

    $("#top-upload-to-cnx, #bottom-upload-to-cnx").click(function(e){
        // reset the warnings
        $("#formentry-title").removeClass("error");
        $("#formentry-title .errortext").hide();
        $("#formentry-ga").removeClass("error");
        $("#formentry-ga .errortext").hide();

        // check required fields
        var valid = true;
        title = $("input[name='title']").val();
        if (title == '(Untitled)' || title.length == 0) {
            $('#formentry-title').addClass('error')
            $("#formentry-title .errortext").show();
            valid = false;
        }
        use_ga_code = $("input#google_code_opener").attr('checked');
        ga_code = $("input[name='google_code']").val();
        if (use_ga_code && ga_code.length == 0) {
            $("#formentry-ga").addClass("error");
            $("#formentry-ga .errortext").show();
            $('#formentry-title').addClass('error')
            $("#formentry-title .errortext").show();
            valid = false;
        }
        if (!valid) {
            return false;
        }

        showWaitMessage();
        $('.forward-button').attr('disabled','disabled');
        $('.forward-button').val('Uploading to Connexions ...');
        $('#back-steps .button').attr('disabled','disabled');
        // the submit here is necessary, because without it, chrome will
        // not submit the form. This has to do with the fact that we are
        // disabling the submit butt
        $('form[name="metadata_form"]').submit();
    });

  // Reveal Google Analtyics field ("Describe your module" page)
  $("#formentry-ga .formlabel").click(function(){
    if ($("#ga-field").css('display') == 'none') {
      $("#ga-field").show();
      $("input[name='google_code_opener']").attr('checked', true);
    } else {
      $("#ga-field").hide();
      $("input[name='google_code_opener']").attr('checked', false);
    }
  });

  // Reveal Featured Links field ("Describe your module" page)
  $("#formentry-fl .formlabel").click(function(){
    if ($("#fl-field").css('display') == 'none') {
      $("#fl-field").show();
      $("input[name='fl_opener']").attr('checked', true);
    } else {
      $("#fl-field").hide();
      $("input[name='fl_opener']").attr('checked', false);
    }
  });

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

    // Show the edit roles form.
    $('#edit-roles').click(function(e) {
        // Populate the fields from the data.
        e.preventDefault();
        var users = get_user_list();
        for (var i in users) {
            $('#roles-table tbody').append(create_row(users[i]));
        };
        populate_roles_checkboxes();
        $('#roles-picker').modal();
    });

    // Hide the edit roles form.
    $('#cancel-roles').click(function(e) {
        e.preventDefault();
        clear_roles_form();
    });

    // Apply the changed roles.
    $('#submit-roles').click(function(e) {
        // Get the roles form data into the right fields
        e.preventDefault();
        populate_roles_fields();
        // Clear the form.
        clear_roles_form();
    });

    // Add a role.
    $('#add-role').click(function(e) {
        e.preventDefault();
        $('#roles-table tbody').append(create_row(''));
        $('#simplemodal-container').css('height', 'auto');
        $(window).trigger('resize.simplemodal');
	    $('#edit-new-username').focus();
    });

    // Simple file upload
    $('input#file-submit').click(function(event){
        event.preventDefault();
        $('input#upload').click();
    });
    
    $('input#presentation-submit').click(function(event){
        event.preventDefault();
        $('input#importer').click();
    });

    $('input#upload').change(function(event){
        showWaitMessage();
        $('form#uploadform').submit(); 
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

    // Show the "Add Featured Links" form.
    $('#show-featuredlinks').click(function(e) {
        e.preventDefault();
        $('#featuredlinks span#create-featuredlinks').show();
        $('#featuredlinks span#edit-featuredlinks').hide();

        template = $('div#featuredlinks');
        $(template).find('input#create-fl-title').removeAttr('value');
        $(template).find('option').each(function(i) {
            $(this).removeAttr('selected');
        });
        $(template).find('input#create-fl-url').removeAttr('value');
        $(template).find('input#create-fl-cnxmoduleid').removeAttr('value');
        $(template).find('input#create-fl-cnxversion').removeAttr('value');
        $(template).find('input#create-fl-useurl').click();

        $(template).find('span#create-featuredlinks').hide();
        $(template).find('span#edit-featuredlinks').show();

        $(template).modal();
    });

    // Hide the "Add Featured Link" form.
    $('#cancel-featuredlinks').click(function(e) {
        e.preventDefault();
        $.modal.close();
    });

    // Apply the "Create or Edit Featured Link" form
    $('#submit-featuredlinks').click(function(e) {
        e.preventDefault();

        // first remove the row
        if (selected_row) {
          $(selected_row).remove();
          selected_row = null;
        }

        // then we add a new row with the changed values
        addFeaturedLink();
        
        $("#show-featuredlinks-form").attr('checked', 'checked');

        $.modal.close();
    });

    // Show the "About Featured Links" overlay
    $('#show-featuredlinks-help').click(function(e) {
        e.preventDefault();
        e.stopPropagation();
        $('#featuredlinks-help').modal();
    });

    // Close the "About Featured Links" overlay
    $('#close-featuredlinks-help').click(function(e) {
        e.preventDefault();
        $.modal.close();
    });

    $('input#create-fl-useurl').click(function(e) {
        $('input#create-fl-cnxmoduleid').attr('disabled', '');
        $('input#create-fl-cnxversion').attr('disabled', '');
        $('input#create-fl-url').removeAttr('disabled');
    });

    $('input#create-fl-usemodule').click(function(e) {
        $('input#create-fl-url').attr('disabled', '');
        $('input#create-fl-cnxmoduleid').removeAttr('disabled');
        $('input#create-fl-cnxversion').removeAttr('disabled');
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

function _doNavAction(event) {
    var element = event.target;
    var target = $(element).attr('href');
    if (!target) {
        target = $(element).attr('url');
    }
    window.location = target;
    event.stopPropagation();
    return true;
}

function _doAction(message, event) {
    // don't let the event propagate up, we handle all actions here.
    // challenge the user before doing the action.
    var element = event.target;
    var c = confirm(message);
    if (c == true) { 
        var target = $(element).attr('href');
        if (!target) {
            target = $(element).attr('url');
        }
        window.location = target;
        event.stopPropagation();
        return true;
    } else {
        event.preventDefault(); 
        event.stopPropagation();
        return false;
    }
}
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
        $('form#uploadform').submit(); 
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

function showWaitMessage() {
    $('#upload-wait').center();
    $('#upload-wait').slideDown();
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

function addFeaturedLink(){
    template = $('#fl-field-template tr').first().clone();
    // get the new element title and clean the template
    title = $('input#create-fl-title').val();
    $('input#create-fl-title').removeAttr('value');
    $(template).find('div.edit-link-title span').html(title);
    $(template).find('input.edit-link-title').attr('value', title);

    // get the category
    category = $('select#create-fl-category').val();
    $('select#create-fl-category').removeAttr('value');
    $(template).find('input.edit-link-category').attr('value', category);
   
    // compute strength
    strength = $('select#create-fl-strength').val();
    $('select#create-fl-strength').removeAttr('value');
    $(template).find('input.edit-link-strength').attr('value', strength);
    base_url = 'static/images/';
    img_prefix = 'strength';
    img_suffix = '.png';
    url = base_url + img_prefix + strength + img_suffix;
    $(template).find('img#edit-link-strength-image')
        .attr('src', url);

    // Use url or module
    useurl = $('input#create-fl-useurl').attr('checked');
    usemodule = $('input#create-fl-usemodule').attr('checked');
    if (useurl == 'checked') {
        value = $('input#create-fl-url').val();
        $('input#create-fl-url').removeAttr('value');
        $(template).find('div.edit-link-title a').attr('href', value);
        $(template).find('input.edit-link-url').attr('value', value);
        $(template).find('input[name="fl_cnxmodule"]').remove();
    }
    if (usemodule == 'checked') {
        module = $('input#create-fl-cnxmoduleid').val();
        $('input#create-fl-cnxmoduleid').removeAttr('value');
        $(template).find('input.edit-link-cnxmodule').attr('value', module);
        $(template).find('div.edit-link-title a').attr('href', module);

        version = $('input#create-fl-cnxversion').val();
        $('input#create-fl-cnxversion').removeAttr('value');
        $(template).find('input.edit-link-cnxversion').attr('value', version);
        $(template).find('input[name="url"]').remove();
    }

    $(template).find('.edit-link').click(editFeaturedLink);
    $(template).find('.remove-link').click(removeFeaturedLink);

    // add the new row to the list of featured links
    $('table#featured-links-table tbody').append(template);
}

function editFeaturedLink(event) {
    event.preventDefault();

    template = $('div#featuredlinks');
    selected_row = $(this).parent().parent();

    title = $(selected_row).find('input.edit-link-title').val();
    $(template).find('input#create-fl-title').attr('value', title);

    type = $(selected_row).find('input.edit-link-category').val();
    $(template).find('option[value="'+type+'"]')
        .attr('selected', 'selected');

    strength = $(selected_row).find('input.edit-link-strength').val();
    $(template).find('option[value="'+strength+'"]')
        .attr('selected', 'selected');

    url = $(selected_row).find('input.edit-link-url').val();
    $(template).find('input#create-fl-url').attr('value', url);

    cnxmodule = $(selected_row).find('input.edit-link-cnxmodule').val();
    $(template).find('input#create-fl-cnxmoduleid')
        .attr('value', cnxmodule);

    cnxversion =  $(selected_row).find('input.edit-link-cnxversion').val();
    $(template).find('input#create-fl-cnxversion')
        .attr('value', cnxversion);

    if (url) {
        $(template).find('input#create-fl-useurl').click();
    } else {
        $(template).find('input#create-fl-usemodule').click();
    }

    $('#featuredlinks span#create-featuredlinks').hide();
    $('#featuredlinks span#edit-featuredlinks').show();
    $('#featuredlinks').modal();
}

function removeFeaturedLink(event) {
    // Remove individual Featured Links ("Describe your module" page).
    // When they're all gone, you can click the checkbox / hide the div again.
    event.preventDefault();
    var c = confirm("Are you sure you want to remove this link?\n\nYou cannot undo its removal, but you can always manually add it again.");
    if (c == true) {
        $(this).closest("tr").hide('fast', function(){
            $(this).remove();
            if ($("#featured-links-table tr").length == 0) {
                $('#show-featuredlinks-form').click();
                $('#show-featuredlinks-form').removeAttr("checked");
            }
        });
    } else {
        return false;
    }
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

