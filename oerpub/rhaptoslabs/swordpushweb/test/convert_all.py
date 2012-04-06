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

formats=[ 'doc', 'url', 'latex', 'odt']
#formats=[ 'url']
#formats=[ 'doc', 'latex', 'odt']

def odt_to_doc(odt_file, doc_folder):
    basename=os.path.basename(odt_file)
    name,extension=os.path.splitext(basename)
    output_file = doc_folder+name+'.doc'
    os.system('./converters/odt2doc -o '+doc_folder+' '+odt_file)
    return output_file

def odt_to_html(odt_file, html_folder):
    basename=os.path.basename(odt_file)
    name,extension=os.path.splitext(basename)
    output_file = html_folder+name+'.html'
    os.system('./converters/odt2html -o '+html_folder+' '+odt_file)
    return output_file

def odt_to_latex(odt_file, latex_folder):
    name, extension = os.path.splitext(odt_file)
    output_file = latex_folder+os.path.basename(name)+'.tex'
    os.system('./converters/abiword -o '+latex_folder+os.path.basename(name)+'.tex --to=tex '+odt_file)
    return output_file

overwrite = False
print(len(sys.argv))
if(len(sys.argv) > 1):
    if(sys.argv[1] == 'ow'):
        overwrite = True
        print('DO OVERWRITE')

odt_folder='./test_files/odt/'
all_tests_odt_files = os.listdir(odt_folder)
i = 0
while(i < len(all_tests_odt_files)):
    current_file = all_tests_odt_files[i]
    name, extension = os.path.splitext(current_file)
    if(extension != '.odt'):
        all_tests_odt_files.remove(current_file)
    else:
        i = i + 1

num_tests = len(all_tests_odt_files)
print('Have '+str(num_tests)+' tests: '+str(all_tests_odt_files))

for form in formats:
    format_folder = './test_files/'+form+'/'
    all_files=os.listdir(format_folder)
    if(form != 'odt'):
        for f in all_files:
            os.remove(format_folder+f)
    for f in all_tests_odt_files:

        output_file = format_folder+os.path.splitext(f)[0]+'.cnxml'
        output_file = output_file + '.cnxml'
        try:
            fp = open(output_file)
            fp.close()
            os.system('python generate_valid_cnxml.py '+gen_file)
        except:
            print('Skipping generating files for '+form+' '+os.path.splitext(f)[0])
            if(overwrite == False):
                continue

        gen_file = ''
        if(form == 'doc'):
            gen_file = odt_to_doc(odt_folder+f, format_folder)
        elif(form == 'url'):
            gen_file = odt_to_html(odt_folder+f, format_folder)
        elif(form == 'latex'):
            gen_file = odt_to_latex(odt_folder+f, format_folder)
        elif(form == 'odt'):
            gen_file = odt_folder+f
        

rids = [ ]

doc_folder='./test_files/doc/'
doc_files = os.listdir(doc_folder)

have_test_file = False
try:
    fp = open('./test_files/gdocs/test_files')
    fp.close()
    have_test_file = True
except:
    print('No gdocs test file')

i = 0
while(i < len(doc_files)):
    current_file = doc_files[i]
    name, extension = os.path.splitext(current_file)
    if(extension != '.doc'):
        doc_files.remove(current_file)
    else:
        i = i + 1

test_folder_name = './test_files/'
for d in doc_files:
    try:
        just_filename=os.path.basename(d)
        just_filename, extension = os.path.splitext(just_filename)
        rid = upload_doc(test_folder_name+'doc/'+d, 'application/msword',just_filename)
        rids.append(rid)
    except KeyboardInterrupt:
        exit()
#    except :
#        print('Error uploading '+just_filename+' to gdocs')

if(have_test_file):
    fp = open('./test_files/gdocs/test_files')
    for url in fp:
        if(url[0] == '#'):
            continue
        match_doc_id = re.match(r'^.*docs\.google\.com/document/d/([^/]+).*$', url)
        if match_doc_id:
            rids.append('document:'+match_doc_id.group(1))
    fp.close()

count = 0
for rid in rids:
    print(rid)
    if(count < len(doc_files)):
        filename = os.path.basename(doc_files[count])
        filename,ext = os.path.splitext(filename)
    else:
        filename = rid[9:]

    valid_filename='./test_files/gdocs/'+filename+'.cnxml'

    gdoc_url = construct_url(rid[9:])
    rid,original_title = get_gdoc(gdoc_url, './test_files/gdocs')
    html_filename = './test_files/gdocs/'+rid[9:]+'.htm'
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
    remove_ids(valid_filename)
    count = count + 1
    os.remove('./test_files/gdocs/'+rid[9:]+'.htm')

