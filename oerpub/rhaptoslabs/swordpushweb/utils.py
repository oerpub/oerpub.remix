import os
import libxml2
import libxslt

current_dir = os.path.dirname(__file__)

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
    edit_history = config.get('edit_history', [])
    edit_history.append((request.session.get("username"),
                         time.asctime(time.gmtime()) + " GMT"))
    config['edit_history'] = edit_history

    save_string = pretty_print_dict(config)
    os.rename(config_filename, backup_filename)
    with open(config_filename, "wt") as fp:
        fp.write(save_string)
        fp.close()


def load_config(request):
    config_filename = request.registry.settings['config_file']
    with open(config_filename, "rb") as fp:
        config = eval(fp.read())
    return config


def escape_system(input_string):
    return '"' + input_string.replace('\\', '\\\\').replace('"', '\\"') + '"'

# Pretty CNXML printing with libxml2 because etree/lxml cannot do pretty printing semantic correct
def clean_cnxml(iCnxml, iMaxColumns=80):
    xsl = os.path.join(current_dir, 'utils_pretty.xsl')
    style_doc = libxml2.parseFile(xsl)
    style = libxslt.parseStylesheetDoc(style_doc)
    doc = libxml2.parseDoc(iCnxml)
    result = style.applyStylesheet(doc, None)
    pretty_cnxml = style.saveResultToString(result)
    style.freeStylesheet()
    doc.freeDoc()
    result.freeDoc()
    return pretty_cnxml

#TODO Marvin: Destroys semantic of xml text nodes. Can be removed in the future.
#http://code.google.com/p/oer-roadmap/issues/detail?id=138
def clean_cnxml_old_before_bug_138(iCnxml, iMaxColumns=80):
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
        return iCnxml

    while True:
        tagStart = cnxml.find("<", cnxmlPos)
        if tagStart == -1:
            break
        tagStop = cnxml.find(">", tagStart)
        preTag = cnxml[cnxmlPos:tagStart] # Everything before the next tag
        tag = cnxml[tagStart:tagStop+1]
        cnxmlPos = tagStop + 1

        # Extract tag name
        if tag[1] == '/':
            tagName = tag[1:3] # / plus first character
        else:
            tagName = tag[1] # first character
        i = len(tagName)+1
        while True:
            character = tag[i]
            if not ((character in "_.-:") or ('a' <= character.lower() <= 'z') or ('0' <= character <= '9')):
                break
            tagName += character
            i += 1

        if tagName == '/code':
            newText += preTag # Do not reformat code lines
        else:
            preTag = preTag.strip()
            if len(preTag) > 0:
                newText += wrap_text(preTag, indent, iMaxColumns) + "\n"

        if (len(tagName) > 0) and (tagName[0] == "/"):
            # Closing tag
            indent -= 1
            newText += " " * indent + tag + "\n"
        else:
            # Opening or self-closing tag or comment
            newText += " " * indent + tag
            if tagName != "code":
                newText += "\n"
            if (tag[-2] != '/') and (tag[:4] != "<!--"):
                indent += 1

    return newText


def add_directory_to_zip(directory, zipFile, basePath=None):
    """
    Add all files and sub-directories from a directory to an open zip
    archive.

    Arguments:

      directory - The directory to add to the zip archive.

      zipFile - The zipfile.ZipFile archive to which to add the
        directory.

      basePath - If not None, this is the path to the directory to
        add. Files from basePath/directory on the file system will be
        added to the zip archive under the path directory.
    """
    import glob, os

    if basePath is None:
        basePath = ''
    if (basePath != '') and (basePath[-1] != '/'):
        basePath += '/'
    basePathLength = len(basePath)

    for pathToFile in glob.glob(os.path.join(basePath + directory, '*')):
        if os.path.isfile(pathToFile):
            zipFile.write(pathToFile, arcname=pathToFile[basePathLength:])
        elif os.path.isdir(pathToFile):
            add_directory_to_zip(pathToFile[basePathLength:], zipFile, basePath=basePath)
