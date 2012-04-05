import os
import sys
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
    os.system('./converters/odt2doc -o '+doc_folder+' '+odt_file)
    basename=os.path.basename(odt_file)
    name,extension=os.path.splitext(basename)
    return doc_folder+name+'.doc'

def odt_to_html(odt_file, html_folder):
    os.system('./converters/odt2html -o '+html_folder+' '+odt_file)
    basename=os.path.basename(odt_file)
    name,extension=os.path.splitext(basename)
    return html_folder+name+'.html'

def odt_to_latex(odt_file, latex_folder):
    name, extension = os.path.splitext(odt_file)
    os.system('./converters/abiword -o '+latex_folder+os.path.basename(name)+'.tex --to=tex '+odt_file)
    return latex_folder+os.path.basename(name)+'.tex'

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
        gen_file = ''
        if(form == 'doc'):
            gen_file = odt_to_doc(odt_folder+f, format_folder)
        elif(form == 'url'):
            gen_file = odt_to_html(odt_folder+f, format_folder)
        elif(form == 'latex'):
            gen_file = odt_to_latex(odt_folder+f, format_folder)
        elif(form == 'odt'):
            gen_file = odt_folder+f
        print('generated file '+gen_file)
        os.system('python generate_valid_cnxml.py '+gen_file)

rids = [ ]

doc_folder='./test_files/doc/'
doc_files = os.listdir(doc_folder)
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

count = 0
for rid in rids:
    print(rid)
    filename = os.path.basename(doc_files[count])
    filename,ext = os.path.splitext(filename)

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

