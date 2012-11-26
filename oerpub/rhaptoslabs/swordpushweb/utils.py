import shutil
import cStringIO
import types
import os
import libxml2
import libxslt
import zipfile
import lxml
import pycurl
import logging

from pyramid.httpexceptions import HTTPFound

from oerpub.rhaptoslabs import sword2cnx

current_dir = os.path.dirname(__file__)
ZIP_PACKAGING = 'http://purl.org/net/sword/package/SimpleZip'

NAMESPACES = {'sword'   : 'http://purl.org/net/sword/',
              'dcterms' : 'http://purl.org/dc/terms/',
              'md'      : 'http://cnx.rice.edu/mdml',
              'xsi'     : 'http://www.w3.org/2001/XMLSchema-instance',
              'oerdc'   : 'http://cnx.org/aboutus/technology/schemas/oerdc',
              'cnxml'   : 'http://cnx.rice.edu/cnxml',
              }

log = logging.getLogger('utils')

def get_files(save_dir):
    files = []
    names = os.listdir(save_dir)
    for name in names:
        tmpfile = open(os.path.join(save_dir, name), 'rb')
        content = tmpfile.read()
        tmpfile.close()
        files.append([name, content])
    return files

def extract_to_save_dir(zip_file, save_dir):
    if not zip_file:
        return
    
    tmp_dir = os.path.join(save_dir, 'tmp')
    for zinfo in zip_file.infolist():
        zip_file.extract(zinfo, tmp_dir)
        fileparts = zinfo.filename.split('/')
        src = os.path.join(tmp_dir, zinfo.filename)
        dest = os.path.join(save_dir, fileparts[-1])
        shutil.move(src, dest)
    shutil.rmtree(tmp_dir, ignore_errors=True)

def create_module_in_2_steps(form, connection, metadata_entry, zip_file, save_dir):
    zip_file = open(os.path.join(save_dir, 'upload.zip'), 'rb')
    data = zip_file.read()
    deposit_receipt = connection.create(
        col_iri = form.data['workspace'],
        payload = data,
        filename = 'upload.zip',
        mimetype = 'application/zip',
        packaging = ZIP_PACKAGING,
        in_progress = True)

    deposit_receipt = connection.update(metadata_entry = metadata_entry,
                                        filename = 'upload.zip',
                                        dr = deposit_receipt,
                                        in_progress=True)
    
    zip_file.close()
    return deposit_receipt

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


def get_cnxml_from_zipfile(zip_file):
    zf = zipfile.ZipFile(zip_file, 'r')
    cnxml = zf.open('index.cnxml')
    zf.close()
    return cnxml


def add_featuredlinks_to_cnxml(cnxml, featuredlinks):
    root = lxml.etree.fromstringlist(cnxml.readlines())
    featuredlinks = ''.join(featuredlinks)
    featuredlinks_element = lxml.etree.fromstring(featuredlinks)
    root.insert(1, featuredlinks_element) 
    return lxml.etree.tostring(root)


def get_files_from_zipfile(zip_file):
    files = []

    zip_archive = zipfile.ZipFile(zip_file, 'r')
    for filename in zip_archive.namelist():
        if filename in ['index.cnxml', 'index.xhtml']:
            continue
        fp = zip_archive.open(filename, 'r')
        files.append((filename, fp.read()))
        fp.close()

    return files


def build_featured_links(data):
    if data is None or len(data.get('featuredlinks')) < 1:
        return ''

    # get featured links from data
    tmp_links = {}
    # first we organise the links by category
    for details in data['featuredlinks']:
        category = details['fl_category']
        tmp_list = tmp_links.get(category, [])
        tmp_list.append(details)
        tmp_links[category] = tmp_list

    links = [u'<featured-links>']
    for category, values in tmp_links.items():
        links.append(u'<link-group type="%s">' %category)
        
        for details in values:
            title = details['fl_title']
            strength = details['fl_strength']
            url = details.get('url', '')
            module = details.get('fl_cnxmodule', '')

            link = ''
            if url:
                link = u'<link url="%s" strength="%s">%s</link>' %(
                    url, strength, title)
            elif module:
                base = 'http://cnx.org/content'
                cnxversion = details.get('fl_cnxversion')
                if not cnxversion:
                    cnxversion = 'latest'
                link = u'<link url="%s/%s/%s/" strength="%s">%s</link>' %(
                    base, module, cnxversion, strength, title)

            links.append(link)

        links.append(u'</link-group>')

    links.append(u'</featured-links>')
    return links


def check_login(request, raise_exception=True):
    # Check if logged in
    for key in ['username', 'password', 'service_document_url']:
        if not request.session.has_key(key):
            if raise_exception:
                raise HTTPFound(location=request.route_url('login'))
            else:
                return False
    return True


def get_connection(session):
    conn = sword2cnx.Connection(session['service_document_url'],
                                user_name=session['username'],
                                user_pass=session['password'],
                                always_authenticate=True,
                                download_service_document=False)
    return conn


def get_metadata_from_repo(session, module_url, user, password):
    conn = get_connection(session)
    resource = conn.get_resource(content_iri = module_url)
    metadata = Metadata(resource.content, module_url, user, password)
    return metadata


class Metadata(dict):

    fields = {'dcterms:title':        types.StringType,
              'dcterms:abstract':     types.StringType,
              'dcterms:language':     types.StringType,
              'oerdc:analyticsCode':  types.StringType,}
    
    contributor_fields = {'dcterms:creator':      types.ListType,
                          'oerdc:maintainer':     types.ListType,
                          'dcterms:rightsHolder': types.ListType,
                          'oerdc:translator':     types.ListType,
                          'oerdc:editor':         types.ListType,}

    def __init__(self, xml_deposit_receipt, module_url, user, password):
        """
        """
        self.encoding = 'utf-8'
        self.raw_data = xml_deposit_receipt
        self.dom = lxml.etree.fromstring(self.raw_data)
        self._parse_metadata()
        self.url = self._module_export_url(module_url)
        self.cnxml = self._fetch_cnxml(self.url,
                                       user.encode(self.encoding),
                                       password.encode(self.encoding))
        if self.cnxml:
            self._parse_featured_link_groups(self.cnxml)
    
    def _parse_metadata(self):
        for name, ftype in self.fields.items():
            value = self._get_value_from_raw(name,
                                             ftype,
                                             self.dom,
                                             NAMESPACES)
            self[name] = value

        self._parse_subjects_and_keywords()
        self._parse_contributors()

    def _parse_subjects_and_keywords(self):
        """ We have to do this, because subjects and keywords are marshalled
            in the same basic element. The only thing distinguishing them is
            the xsi:type.
        """
        elements = self.dom.findall('dcterms:subject', namespaces=NAMESPACES)
        self._get_subjects(elements)
        self._get_keywords(elements)

    def _parse_contributors(self):
        for name, ftype in self.contributor_fields.items():
            value  = []
            elements = self.dom.findall(name, namespaces=NAMESPACES)
            for e in elements:
                tmp_key = '{%s}id' % NAMESPACES['oerdc']
                tmp_val = e.attrib.get(tmp_key, '')
                if tmp_val:
                    value.append(tmp_val)
            self[name] = value

    def _parse_featured_link_groups(self, cnxml):
        dom = lxml.etree.fromstring(cnxml)
        links = []
        for e in dom.xpath('//cnxml:link-group', namespaces=NAMESPACES):
            group = FeaturedLinkGroup(e)
            links.append(group)
        self['featured_link_groups'] = links

    def _get_value_from_raw(self, name, ftype, dom, namespaces):
        value = ''
        elements = dom.findall(name, namespaces=namespaces)
        if elements:
            if ftype == types.ListType:
                value = []
                for e in elements:
                    value.append(e.text)
            else:
                value = elements[0].text
        return value

    def _get_keywords(self, elements):
        value = []
        elements = [e for e in elements if not e.attrib]
        if elements:
            for e in elements:
                value.append(e.text)
        self['keywords'] = value

    def _get_subjects(self, elements):
        value = []
        elements = [e for e in elements if e.attrib]
        if elements:
            for e in elements:
                value.append(e.text)
        self['subjects'] = value

    def _module_export_url(self, url):
        module_url = '/'.join(url.split('/')[:-1])
        module_url = '%s/module_export' % module_url
        return (module_url).encode(self.encoding)

    def _fetch_cnxml(self, url, user, password):
        buff = cStringIO.StringIO()
        pc = pycurl.Curl()
        pc.setopt(pc.WRITEFUNCTION, buff.write)
        pc.setopt(pc.URL, url)
        pc.setopt(pc.USERPWD, '%s:%s' % (user, password))
        pc.setopt(pc.POSTFIELDS, 'format=plain')
        pc.perform()

        if pc.getinfo(pc.HTTP_CODE) == 200:
            result = buff.getvalue()
        else:
            result = ''
        return result

class FeaturedLinkGroup(object):
    
    def __init__(self, element):
        self.element = element
        self.group_type = self.parse_group_type(self.element)
        self.links = self.parse_links(self.element)

    def parse_group_type(self, element):
        return element.attrib['type']

    def parse_links(self, element):
        links = []
        for e in element.xpath('cnxml:link', namespaces=NAMESPACES):
            links.append(FeaturedLink(e, self.group_type))
        return links
    
class FeaturedLink(object):
    def __init__(self, element, category):
        self.element = element
        self.category = category
        self.title = self.parse_title(self.element)
        self.url = self.parse_url(self.element)
        self.strength = self.parse_strength(self.element)
        self.module = self.parse_module(self.element)
        self.cnxversion = self.parse_cnxversion(self.element)
    
    def parse_title(self, element):
        return element.text

    def parse_url(self, element):
        prefix = 'http://'
        url = element.attrib.get('url', '')
        if url and not url.startswith(prefix):
            url = '%s%s' % (prefix, url)
        return url

    def parse_strength(self, element):
        return element.attrib['strength']

    def parse_module(self, element):
        return element.attrib.get('module', '')

    def parse_cnxversion(self, element):
        return element.attrib.get('cnxversion', '')
