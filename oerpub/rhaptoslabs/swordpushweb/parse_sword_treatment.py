def __extract_from_substrings(treatment, substrStart, substrStop):
    start_pos = treatment.find(substrStart)
    if start_pos == -1:
        raise ValueError, "Start substring not found"
    start_pos += len(substrStart)
    stop_pos = treatment.find(substrStop, start_pos)
    if stop_pos == -1:
        raise ValueError, "Stop substring not found"
    return treatment[start_pos:stop_pos]


def __extract_module_title(treatment):
    # Read module title
    # TODO: Check what happens if there is a ' in the module title
    try:
        return __extract_from_substrings(treatment, "Module '", "' was imported")
    except ValueError:
        return 'ERROR'


def __extract_module_url(treatment):
    # Read module URL
    try:
        return __extract_from_substrings(treatment, 'You can <a href="', '">preview your module here</a>')
    except ValueError:
        return 'ERROR'


def markdown(treatment):
    # TODO: Test
    import markdown
    treatment = [i.lstrip() for i in treatment.split('\n')]
    treatment = markdown.markdown('\n'.join(treatment))

    return {
        'module_title': __extract_module_title(treatment),
        'module_url': __extract_module_url(treatment),
        'treatment': treatment,
    }


def __parse_version_1_0(iTreatment, iPublicationRequirementsString, iRoleRequestPrefix, iRoleRequestHasEmail):
    # Strip out the early bits to prevent the module title from interfering with anything else
    import HTMLParser
    h = HTMLParser.HTMLParser()
    iTreatment = h.unescape(iTreatment)

    treatment = iTreatment[iTreatment.find(iPublicationRequirementsString):]

    count = 0
    requirements = []
    while True:
        count += 1
        substr = "%i. "%count
        start_pos = treatment.find(substr)
        if start_pos == -1:
            break
        start_pos += len(substr)

        requirement_licence = 'Author ('
        requirement_role_request = iRoleRequestPrefix
        if treatment[start_pos:start_pos+len(requirement_licence)] == requirement_licence:
            #1. Author (Carl Scheffler, account:cscheffler), will need to <a href="http://cnx.org/Members/cscheffler/module.2011-11-02.1518791239/module_publish">sign the license here.</a>
            # Parse author info and request that they sign the licence
            full_name_start = start_pos+len(requirement_licence)
            substr = '), will need to <a href="'
            username_stop = treatment.find(substr, start_pos)
            url_start = username_stop + len(substr)
            url_stop = treatment.find('"', url_start)
            full_name_stop = treatment.rfind(', account:', full_name_start, username_stop)
            username_start = full_name_stop + len(', account:')
            full_name = treatment[full_name_start:full_name_stop]
            username = treatment[username_start:username_stop]
            licence_url = treatment[url_start:url_stop]
            requirements.append({'type': 'licence', 'name': full_name, 'username': username, 'url': licence_url})
        elif treatment[start_pos:start_pos+len(requirement_role_request)] == requirement_role_request:
            # Parse role requests
            # TODO: What happens when one person must agree to multiple roles?
            role_start = start_pos + len(requirement_role_request)
            substr = ', '
            role_stop = treatment.find(substr, role_start)
            full_name_start = role_stop + len(substr)
            substr = ' (account:'
            full_name_stop = treatment.find(substr, full_name_start)
            username_start = full_name_stop + len(substr)
            if iRoleRequestHasEmail:
                substr = ', email:'
                username_stop = treatment.find(substr, username_start)
                email_start = username_stop + len(substr)
                email_stop = treatment.find('),', email_start)
                email = treatment[email_start:email_stop]
            else:
                username_stop = treatment.find('),', username_start)
                email = ''
            substr = '<a href="'
            url_start = treatment.find(substr, username_stop) + len(substr)
            url_stop = treatment.find('"', url_start)
            role = treatment[role_start:role_stop]
            full_name = treatment[full_name_start:full_name_stop]
            username = treatment[username_start:username_stop]
            agree_url = treatment[url_start:url_stop]
            requirements.append({'type': 'role_request', 'role': role, 'name': full_name, 'username': username, 'email': email, 'url': agree_url})
        else:
            print 'WARNING: Could not parse treatment requirement line:'

    return {
        'module_title': __extract_module_title(iTreatment),
        'module_url': __extract_module_url(iTreatment),
        'requirements': requirements,
    }


def cnx_1_0(treatment):
    #5. You cannot publish with pending role requests. Contributor, Daniel Williamson (account:user85),
    #must <a href="http://50.57.120.10:8080/Members/user1/module.2011-10-06.9527952926/collaborations?user=user85">agree to thw pending requests</a>.
    return __parse_version_1_0(
        treatment,
        iPublicationRequirementsString='Publication requirements:',
        iRoleRequestPrefix='You cannot publish with pending role requests. ',
        iRoleRequestHasEmail=False,
    )


def test_server_1_0(treatment):
    #4. Contributor, firstname2 lastname2 (account:user2, email:useremail2@localhost.net), must <a href="http://50.57.120.10:8080/Members/user1/module.2011-11-02.5929140506/collaborations?user=user2">agree to be associated with this module</a>.
    return __parse_version_1_0(
        treatment,
        iPublicationRequirementsString='Before publishing:',
        iRoleRequestPrefix='',
        iRoleRequestHasEmail=True,
    )
