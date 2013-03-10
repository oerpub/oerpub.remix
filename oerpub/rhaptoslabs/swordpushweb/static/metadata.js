// JavaScript for the metadata page template


//
// Edit Roles dialog box
//

/* Translate between the roles form and the roles list in the sidebar. This can
 * be achieved more efficiently than here by translating into some intermediate
 * structure, but this way is more readable and debuggable. */

var roles = new Array('authors', 'maintainers', 'copyright', 'editors', 'translators');
var required_roles = new Array('authors', 'maintainers', 'copyright');

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
    // Show the edit roles form.
    $('#edit-roles').click(function(e) {
        // Populate the fields from the data.
        e.preventDefault();
        var users = get_user_list();
        for (var i in users) {
            $('#roles-table tbody').append(create_row(users[i]));
        };
        populate_roles_checkboxes();
        $('#roles-picker').modal({'minHeight':'514px'});
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
});


//
// Google Analtyics logic
//

$(document).ready(function()
{
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

});

//
// Upload to CNX handler
//

$(document).ready(function()
{
    // potentially dead ... #top-upload-to-cnx and #bottom-upload-to-cnx are MIA
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

});

//
// Featured Links logic
//

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
    $('#featuredlinks').modal({'minHeight':'210px'});
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

$(document).ready(function()
{
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

        $(template).modal({'minHeight':'210px'});
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
        $('#featuredlinks-help').modal({'minHeight':'514px'});
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

});

//
//  Next and Back button futzing
//

$(document).ready(function()
{
    // "Finish: Upload" button ("Describe your module" page)
    $("#metadata .forward-button").click(function(){
      $('.forward-button').attr('disabled','disabled');
      $('.forward-button').val('Uploading to Connexions ...');
      $('#back-steps .button').attr('disabled','disabled');
    });

});
