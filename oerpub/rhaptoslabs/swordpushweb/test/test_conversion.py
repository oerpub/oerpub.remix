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
#all_repos=os.listdir(repo_location)
#for repo in all_repos:
#    full_path=repo_location+repo
#    if os.path.isdir(full_path):
#        sys.path.append(full_path)
#        sys.path.append(full_path+'/src')

sys.path.append('../')
sys.path.append('../../../../../oerpub.rhaptoslabs.html_gdocs2cnxml/src')
sys.path.append('../../../../../rhaptos.cnxmlutils')

from rhaptos.cnxmlutils.odt2cnxml import transform
from oerpub.rhaptoslabs.html_gdocs2cnxml.htmlsoup2cnxml import htmlsoup_to_cnxml
from oerpub.rhaptoslabs.html_gdocs2cnxml.gdocs2cnxml import gdocs_to_cnxml
from utils import clean_cnxml, escape_system
from lxml import etree

test_folder_name='test_files/'

class SimpleTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_doc(self):
        doc_files=os.listdir(test_folder_name+'doc/')
        i=0
# Find only .odt files in the testing folder for odt
        while(i < len(doc_files)):
            f=doc_files[i]
            filename, extension = os.path.splitext(f)
            if(extension != '.doc'):
                doc_files.remove(f)
            else:
                i=i+1

        for f in doc_files:
            original_filename=test_folder_name+'doc/'+f
            filename, extension = os.path.splitext(original_filename)

            valid_filename=filename+'.cnxml'
            output_filename=filename+'.tmp'
            doc_filename = original_filename
            diff_filename = filename+'.diff'
            err_filename = filename+'.err'

            odt_filename= filename+'.odt'
            command = '/usr/bin/soffice --headless --nologo --nofirststartwizard "macro:///Standard.Module1.SaveAsOOO(' + os.getcwd()+'/'+original_filename + ',' + os.getcwd()+'/'+odt_filename + ')"'
            os.system(command)

            try:
                open(valid_filename, 'r')
            except IOError as e:
                print('Missing valid file ('+valid_filename+') for testing '+original_filename)
                return

            tree, files, errors = transform(odt_filename)
            cnxml = clean_cnxml(etree.tostring(tree))
            output=open(output_filename,'w')
            output.write(cnxml)
            output.close()
            process = subprocess.Popen(['diff',valid_filename,output_filename], shell=False, stdout=subprocess.PIPE)
            std_output = process.communicate()

            if(std_output[0] != None and len(std_output[0]) != 0):
                diff_output=open(diff_filename,'w')
                diff_output.write(std_output[0])
                diff_output.close()
                print('Differences in the testing of '+original_filename+', information on those differences has been placed in '+diff_filename)
            elif(std_output[1] != None and len(std_output[1]) != 0):
                err_output=open(err_filename,'w')
                err_output.write(std_output[1])
                err_output.close()
                print('Error(s) occurred while attempting to test for differences in CNXML output of '+original_filename+', information on these errors are in '+err_filename)


    def test_odt(self):
        odt_files=os.listdir(test_folder_name+'odt/')
        i=0
# Find only .odt files in the testing folder for odt
        while(i < len(odt_files)):
            f=odt_files[i]
            filename, extension = os.path.splitext(f)
            if(extension != '.odt'):
                odt_files.remove(f)
            else:
                i=i+1

        for f in odt_files:
            original_filename=test_folder_name+'odt/'+f
            filename, extension = os.path.splitext(original_filename)

            valid_filename=filename+'.cnxml'
            output_filename=filename+'.tmp'
            odt_filename = original_filename
            diff_filename = filename+'.diff'
            err_filename = filename+'.err'

            try:
                open(valid_filename, 'r')
            except IOError as e:
                print('Missing valid file ('+valid_filename+') for testing '+original_filename)
                return

            tree, files, errors = transform(odt_filename)
            cnxml = clean_cnxml(etree.tostring(tree))
            output=open(output_filename,'w')
            output.write(cnxml)
            output.close()
            process = subprocess.Popen(['diff',valid_filename,output_filename], shell=False, stdout=subprocess.PIPE)
            std_output = process.communicate()

            if(std_output[0] != None and len(std_output[0]) != 0):
                diff_output=open(diff_filename,'w')
                diff_output.write(std_output[0])
                diff_output.close()
                print('Differences in the testing of '+original_filename+', information on those differences has been placed in '+diff_filename)
            elif(std_output[1] != None and len(std_output[1]) != 0):
                err_output=open(err_filename,'w')
                err_output.write(std_output[1])
                err_output.close()
                print('Error(s) occurred while attempting to test for differences in CNXML output of '+original_filename+', information on these errors are in '+err_filename)
                

    def test_url(self):
        url_files=os.listdir(test_folder_name+'url/')
        i=0

        while(i < len(url_files)):
            f=url_files[i]
            filename, extension = os.path.splitext(f)
            if(extension != ''):
                url_files.remove(f)
            else:
                i=i+1

        for f in url_files:
            input_file=open(test_folder_name+'url/'+f,'r')
            url=input_file.readline()
            input_file.close()

            output_filename=test_folder_name+'url/'+f+'.cnxml'
            valid_filename=test_folder_name+'url/'+f+'.cnxml'
            output_filename=test_folder_name+'url/'+f+'.tmp'
            diff_filename = test_folder_name+'url/'+f+'.diff'
            err_filename = test_folder_name+'url/'+f+'.err'

            import_opener = urllib2.build_opener()
            import_opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            try:
                import_request = import_opener.open(url)
                html = import_request.read()

                # transformation            
                cnxml, objects, html_title = htmlsoup_to_cnxml(
                html, bDownloadImages=True, base_or_source_url=url)

                cnxml = clean_cnxml(cnxml)


                output=open(output_filename,'w')
                output.write(cnxml)
                output.close()

                process = subprocess.Popen(['diff',valid_filename,output_filename], shell=False, stdout=subprocess.PIPE)
                std_output = process.communicate()

                if(std_output[0] != None and len(std_output[0]) != 0):
                    diff_output=open(diff_filename,'w')
                    diff_output.write(std_output[0])
                    diff_output.close()
                    print('Differences in the testing of '+f+', information on those differences has been placed in '+diff_filename)
                elif(std_output[1] != None and len(std_output[1]) != 0):
                    err_output=open(err_filename,'w')
                    err_output.write(std_output[1])
                    err_output.close()
                    print('Error(s) occurred while attempting to test for differences in CNXML output of '+f+', information on these errors are in '+err_filename)

            except urllib2.URLError, e:
                print('URL '+url+' could not be opened')
                quit()

    def test_gdocs(self):
        gdoc_files=os.listdir(test_folder_name+'gdocs/')
        i=0

        while(i < len(gdoc_files)):
            f=gdoc_files[i]
            filename, extension = os.path.splitext(f)
            if(extension != '.gdoc'):
                gdoc_files.remove(f)
            else:
                i=i+1

        for f in gdoc_files:
            original_filename=test_folder_name+'gdocs/'+f
            filename, extension = os.path.splitext(original_filename)

            valid_filename=filename+'.cnxml'
            output_filename=filename+'.tmp'
            diff_filename = filename+'.diff'
            err_filename = filename+'.err'

            fp=open(original_filename, 'r')
            html=fp.read()
            fp.close()
            cnxml, objects = gdocs_to_cnxml(html, bDownloadImages=True)
            cnxml = clean_cnxml(cnxml)

            output=open(output_filename,'w')
            output.write(cnxml)
            output.close()

            process = subprocess.Popen(['diff',valid_filename,output_filename], shell=False, stdout=subprocess.PIPE)
            std_output = process.communicate()

            if(std_output[0] != None and len(std_output[0]) != 0):
                diff_output=open(diff_filename,'w')
                diff_output.write(std_output[0])
                diff_output.close()
                print('Differences in the testing of '+f+', information on those differences has been placed in '+diff_filename)
            elif(std_output[1] != None and len(std_output[1]) != 0):
                err_output=open(err_filename,'w')
                err_output.write(std_output[1])
                err_output.close()
                print('Error(s) occurred while attempting to test for differences in CNXML output of '+f+', information on these errors are in '+err_filename)


if __name__ == '__main__':
    unittest.main()
