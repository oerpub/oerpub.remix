import os
import sys
import re
sys.path.append('../splitter')
sys.path.append('../../../../../oerpub.rhaptoslabs.html_gdocs2cnxml/src')
sys.path.append('../../../../../rhaptos.cnxmlutils')
sys.path.append('../../')
sys.path.append('../')
sys.path.append('./')
from splitter import get_gdoc, upload_doc, construct_url
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs2cnxml import gdocs_to_cnxml
from utils import clean_cnxml, escape_system
from test_conversion import validate_cnxml, remove_ids

url='https://docs.google.com/document/d/1tiZR1fhBl3ZQ_UaQ5sRDA3gSs_7LjgtTITkBAGjuTpI/edit'
#url='https://docs.google.com/document/d/1Gw9j1J-_d5YQoq6SIc3Az2hiVlwtvVcJkXfYKDR_zBM/edit'

match_doc_id = re.match(r'^.*docs\.google\.com/document/d/([^/]+).*$', url)
rid='document:'+match_doc_id.group(1)

print(rid)
filename = rid[9:]
valid_filename='valid.cnxml'
gdoc_url = construct_url(rid[9:])
print(gdoc_url)
rid,original_title = get_gdoc(url, './')
html_filename = './'+rid[9:]+'.htm'
html_file = open(html_filename, 'r')
try:
    html = html_file.read()
    html_file.flush()
finally:
    html_file.close()

cnxml, objects = gdocs_to_cnxml(html, bDownloadImages=True)
cnxml = clean_cnxml(cnxml)
validate_cnxml(cnxml)

output=open(valid_filename,'w')
output.write(cnxml)
output.close()


