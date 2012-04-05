import unittest
import sys
import os
import subprocess
import urllib2

eggs_location= '../../../../../../eggs/'
repo_location='../../../../../'

all_eggs=os.listdir(eggs_location)
for egg in all_eggs:
    full_path=eggs_location+egg
    if os.path.isdir(full_path):
        sys.path.append(full_path)

sys.path.append('../')
sys.path.append('../../../../../oerpub.rhaptoslabs.html_gdocs2cnxml/src')
sys.path.append('../../../../../rhaptos.cnxmlutils')
sys.path.append('../../../../../oerpub.rhaptoslabs.latex2cnxml/src/oerpub/rhaptoslabs')

from rhaptos.cnxmlutils.odt2cnxml import transform
from latex2cnxml.latex2cnxml import latex_to_cnxml
from oerpub.rhaptoslabs.html_gdocs2cnxml.htmlsoup2cnxml import htmlsoup_to_cnxml
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs2cnxml import gdocs_to_cnxml
from utils import clean_cnxml, escape_system
from lxml import etree

def remove_ids(filename):
    command='xsltproc -o tmp.xml removeid.xsl '+filename
    os.system(command)
    os.system('mv tmp.xml '+filename)
    

if(len(sys.argv) != 2):
    print('usage: python generate_valid_cnxml.py file')
    quit()

filename=sys.argv[1]
name, extension = os.path.splitext(filename)
if(extension == '.odt' or extension == '.doc'):

    if(extension == '.doc'):
        doc_folder = os.getcwd()+'/'+os.path.dirname(name)
        os.system('./converters/doc2odt -o '+doc_folder+' '+os.getcwd()+'/'+filename)
        #command = '/usr/bin/soffice --headless --nologo --nofirststartwizard "macro:///Standard.Module1.SaveAsOOO(' + os.getcwd()+'/'+filename + ',' + os.getcwd()+'/'+name+'.odt' + ')"'
        #os.system(command)
        filename=name+'.odt'


    valid_filename=name+'.cnxml'
    tree, files, errors = transform(filename)
    cnxml = clean_cnxml(etree.tostring(tree))
    output=open(valid_filename,'w')
    output.write(cnxml)
    output.close()
    remove_ids(valid_filename)
    if(extension == '.doc'):
        os.remove(os.getcwd()+'/'+name+'.odt')

elif(extension == '.tex'):
    valid_filename=name+'.cnxml'
    fp = open(filename, 'r')
    latex_archive = fp.read()
    fp.close()

    # LaTeX 2 CNXML transformation
    cnxml, objects = latex_to_cnxml(latex_archive, filename)

    cnxml = clean_cnxml(cnxml)
    output = open(valid_filename, 'w')
    output.write(cnxml)
    output.close()
    remove_ids(valid_filename)

elif(extension=='.html'):
    print('Assuming this is a file containing a URL')
    f = filename
    input_file=open(f,'r')

    name,extension = os.path.splitext(filename)
    valid_filename=name+'.cnxml'

    try:
        html = input_file.read()
        input_file.close()

        # transformation            
        cnxml, objects, html_title = htmlsoup_to_cnxml(
        html, bDownloadImages=True, base_or_source_url=filename)

        cnxml = clean_cnxml(cnxml)

        output=open(valid_filename,'w')
        output.write(cnxml)
        output.close()
        remove_ids(valid_filename)
    except urllib2.URLError, e:
        print('URL '+url+' could not be opened')
        quit()

print('Done. Valid output has been placed in '+valid_filename)

