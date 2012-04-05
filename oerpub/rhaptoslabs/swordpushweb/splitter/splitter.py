'''
Testing and development of GDocs to CNXML transformation.

Transforms all GDocs URLs in testbed folder to CNXML.
Validates the result with Jing Relax NG.

Input are all URLs in TESTBED_INPUT_URLS_FILE.

CNXML results are saved as in a directory named like the GDocs ID as:
  .xml             -  the CNXML result
  .htm             -  the raw HTML GDocs input format before transformation
  .png/.jpg/.gif   -  including all images
  .log             -  Jing Relax NG validation results

 If there is no error during validation the .log file has zero bytes.

Created on 14.09.2011

@author: Marvin Reimer
'''



import sys
import os
import HTMLParser

sys.path.append('/home/jmg3/swordpushweb-buildout/src/oerpub.rhaptoslabs.html_gdocs2cnxml/src/oerpub/rhaptoslabs/html_gdocs2cnxml/')

import subprocess
import re
import shutil
from gdocs2cnxml import gdocs_to_cnxml
from my_gdocs_authentication import getAuthorizedGoogleDocsClient
import gdata

TESTBED_INPUT_DIR = "./"  # the testbed folder
TESTBED_INPUT_URLS_FILE = "gdocs_urls.cfg"

class SectionParser(HTMLParser.HTMLParser):

    def __init__(self, html):
        HTMLParser.HTMLParser.__init__(self)
        self.last_pos = -1
        self.collect_subsections = [ ]
        self.html = html
        self.head = None
        self.tail = '</body></html>'
        

    def handle_starttag(self, tag, attrs):
        if(tag == 'h1' or tag == 'h2'):
            current_pos = self.getpos()[1]
            if(self.last_pos != -1):
                # create new section
                substr = self.html[self.last_pos:current_pos]
                self.collect_subsections.append(substr)
            else:
                self.head = self.html[0:current_pos]
            self.last_pos = current_pos
    def get_last_pos(self):
        return self.last_pos

    def run(self):
        self.feed(self.html)
        if(len(self.html)-1 > self.last_pos):
            self.collect_subsections.append(self.html[self.last_pos:len(self.html)-1])
        result = [ ]
        count = 0
        for sect in self.collect_subsections:
            full_sect = self.head+sect
            if(count != len(self.collect_subsections)-1):
                full_sect = full_sect + self.tail
            result.append(full_sect)
            count = count + 1

        return result

def divide_sections(html):
    parser=SectionParser(html)
    sections = parser.run()
    return sections

# tests if java is installed and available at commandline
def java_installed():
    error = True
    try:
        p = subprocess.Popen('java -version', shell=True, stdout=subprocess.PIPE)
        error = p.communicate()[1]
    finally:
        return not error

# Be careful with this command!
def delete_all_contents_of_folder(folder):
    if os.path.isdir(folder):
        for root, dirs, files in os.walk(folder):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

# prints a status message surrounded by some lines
def print_status(status_message):
    print '=' * 79
    print status_message
    print '=' * 79

# Jing validation and save log file
def jing_validate_file(xml_filename, log_filename):
    # build the java commandline string
    jing_jar_filename = os.path.join('jing', 'jing.jar')
    jing_rng_filename = os.path.join('jing', 'cnxml-jing.rng')
    java_cmd = 'java -jar %s %s %s' % (jing_jar_filename, jing_rng_filename, xml_filename)
    # validate XML and save log file
    jing_log_file = open(log_filename, 'w')
    try:
        p = subprocess.Popen(java_cmd, shell=True, stdout=subprocess.PIPE)
        jing_log, error_data = p.communicate()
        if not error_data:
            jing_log_file.write(jing_log)
        else:
            jing_log_file.write(error_data)
    finally:
        jing_log_file.close()

def get_gdoc(gdoc_url, output_folder):
    gd_client = getAuthorizedGoogleDocsClient()
    match_doc_id = re.match(r'^.*docs\.google\.com/document/d/([^/]+).*$', gdoc_url)
    if match_doc_id:
        doc_id = match_doc_id.group(1)

        # create a sub directory named like the ID
        doc_output_dir = output_folder
        try:
            os.mkdir(doc_output_dir)
        except OSError:
            pass    # If subdirectory already exists do nothing

        doc_key = 'document:' +  doc_id

        # get the Google Docs Entry
        #gd_entry = gd_client.GetDoc(doc_key)
        gd_entry = gd_client.get_resource_by_id(doc_key)

        # Get the contents of the document
        gd_entry_url = gd_entry.content.src     # should be the same as url, but better ask API for url
        html = gd_client._get_content(gd_entry_url)     # requires a URL

        html_filename = os.path.join(doc_output_dir, doc_id +'.htm')
        html_file = open(html_filename, 'w')
        try:
            html_file.write(html)
            html_file.flush()
        finally:
            html_file.close()
        return (gd_entry.resource_id.text, gd_entry.title.text)

    else:
        print 'Error matching doc id in get_gdoc'
        quit()

def upload_doc(filename, handle, new_title):
    gd_client = getAuthorizedGoogleDocsClient()
    document = gdata.docs.data.Resource(type='document', title=new_title)
    path=filename
    media=gdata.data.MediaSource()
    media.SetFileHandle(path, handle)
    document = gd_client.CreateResource(document,media=media)
    return document.resource_id.text

def construct_url(rid):
    return 'https://docs.google.com/document/d/'+rid+'/edit'

# converts all URLs in testbed input file to CNXML output folder
def main():
    # keep sure Java is installed (needed for Jing)
    if not java_installed():
        print "ERROR: Could not find Java. Please keep sure that Java is installed and available."
        exit(1)
    # delete the contents of the testbed folder
    delete_all_contents_of_folder('./gdoc_output')
    # login to gdocs and get a client object
    gd_client = getAuthorizedGoogleDocsClient()
    # open file with GDocs public documents URLs (<- the testbed for GDocs)
    url_file = open(os.path.join(TESTBED_INPUT_DIR, TESTBED_INPUT_URLS_FILE))
    for url in url_file:
        if not url.startswith('#'):   # ignore comments
            # check if we really have a gdocs document with an ID
            # Get the ID out of the URL with regular expression
            rid,original_title = get_gdoc(url, './gdoc_output')
            html_filename = os.path.join('./gdoc_output', rid[9:]+'.htm')
            html_file = open(html_filename, 'r')
            try:
                html = html_file.readlines()
                html_file.flush()
            finally:
                html_file.close()
            inline_html = ''
            for line in html:
                if(line[len(line)-1] == '\n'):
                    inline_html = inline_html + line[0:len(line)-1]
                else:
                    inline_html = inline_html + line

            sections = divide_sections(inline_html)
            sect_num = 0
            for sect in sections:
                html_filename = './gdoc_output/'+rid[9:]+'_sect_'+str(sect_num)+'.htm'
                html_file = open(html_filename, 'w')
                try:
                    html_file.write(sect)
                    html_file.flush()
                finally:
                    html_file.close()

                sect_num = sect_num + 1

            sect_num = 0
            for sect in sections:
                html_filename = './gdoc_output/'+rid[9:]+'_sect_'+str(sect_num)+'.htm'
                try:
                    upload_doc(html_filename, 'text/html', original_title+', Section '+str(sect_num))
                except KeyboardInterrupt:
                    exit()
                except:
                    print('Error uploading section '+str(sect_num)+'. Are there images in there?')
                    
                os.remove(html_filename)
                sect_num = sect_num + 1



    print_status('Finished!')


if __name__ == "__main__":
    main()
