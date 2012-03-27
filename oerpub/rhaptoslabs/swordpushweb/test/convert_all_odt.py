import os

formats=[ 'doc', 'url', 'latex' ]
#formats=[ 'url' ]

def odt_to_doc(odt_file, doc_folder):
    os.system('./converters/odt2doc -o '+doc_folder+' '+odt_file)
    basename=os.path.basename(odt_file)
    name,extension=os.path.splitext(basename)
    return doc_folder+name+'.doc'

def odt_to_html(odt_file, html_folder):
    os.system('./converters/odt2html -o '+html_folder+' '+odt_file)
    basename=os.path.basename(odt_file)
    name,extension=os.path.splitext(basename)
    os.system('touch '+html_folder+name)
    os.system('echo file://'+os.getcwd()+'/'+html_folder+name+'.html > '+html_folder+name)
    return html_folder+name

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
        print('generated file '+gen_file)
        os.system('python generate_valid_cnxml.py '+gen_file)

