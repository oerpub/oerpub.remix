def pretty_print_dict(x, indent=0):
    output = '{'
    indentString = '    ' * (indent+1)
    for key in x.keys():
        output += '\n' + indentString + '"' + key + '": '
        value = x[key]
        if type(value) is dict:
            output += pretty_print_dict(value, indent+1)
        else:
            output += repr(value)
        output += ','
    output += '\n' + '    ' * indent + '}'
    return output


def save_config(config, request):
    import os, time

    config_filename = request.registry.settings['config_file']
    backup_filename = request.registry.settings['config_file'] + '~'

    # Update edit history
    config['edit_history'].append((request.session.get("username"), time.asctime(time.gmtime()) + " GMT"))

    save_string = pretty_print_dict(config)
    os.rename(config_filename, backup_filename)
    with open(config_filename, "wt") as fp:
        fp.write(save_string)


def load_config(request):
    config_filename = request.registry.settings['config_file']
    with open(config_filename, "rb") as fp:
        config = eval(fp.read())
    return config


def escape_system(input_string):
    return '"' + input_string.replace('\\', '\\\\').replace('"', '\\"') + '"'


def clean_cnxml(iCnxml, iMaxColumns=80):
    """
    iMaxColumns -- maximum number of columns to allow when wrapping text.

    return metadata section, clean cnxml
    """
    import re # Perl regular expressions

    cnxml = iCnxml

    # Remove metadata
    #metaStart = cnxml.find("<metadata ")
    #if metaStart != -1:
    #    metaStop = cnxml.find("</metadata>") + 11
    #    metaText = cnxml[metaStart:metaStop]
    #    cnxml = cnxml[:metaStart] + "<metadata/>" + cnxml[metaStop:]
    #else:
    #    metaText = ""

    # Force XML tags to be on 1 line
    closePos = -1
    oldCnxml = cnxml
    cnxml = ""
    while True:
        startPos = closePos + 1
        openPos = oldCnxml.find("<", startPos)
        if openPos == -1:
            break
        closePos = oldCnxml.find(">", openPos+1)
        if closePos == -1:
            break
        cnxml += oldCnxml[startPos:openPos]
        cnxml += re.sub('\\s+', ' ', oldCnxml[openPos:closePos+1])
    cnxml += oldCnxml[startPos:]

    # Clean up XML tag indentation and text wrapping
    tagsNoNewLine = ["emphasis"] # FIXME: this is unused
    indent = 0
    tagStack = []
    cnxmlPos = 0
    newText = ""

    def wrap_text(iCnxml, iIndent, iColumns):
        import textwrap
        indent = ""#" " * iIndent
        return ''.join(textwrap.wrap(re.sub('\\s+', ' ', iCnxml), iColumns,
                                     initial_indent=indent,
                                     subsequent_indent="\n" + indent))

    while True:
        tagStart = cnxml.find("<", cnxmlPos)
        if tagStart == -1:
            break
        tagStop = cnxml.find(">", tagStart)
        preTag = cnxml[cnxmlPos:tagStart].strip() # Everything before the next tag
        tag = cnxml[tagStart:tagStop+1]
        cnxmlPos = tagStop + 1

        if len(preTag) > 0:
            newText += wrap_text(preTag, indent, iMaxColumns) + "\n"

        if tag[1] == "/":
            # Closing tag
            indent -= 1
            newText += " " * indent + tag + "\n"
        else:
            # Opening or self-closing tag or comment
            newText += " " * indent + tag + "\n"
            if (tag[-2] != '/') and (tag[:4] != "<!--"):
                indent += 1

    return newText
