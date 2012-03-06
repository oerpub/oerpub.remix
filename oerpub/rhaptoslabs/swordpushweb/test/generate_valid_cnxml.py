import unittest
import sys
import os
import subprocess


eggs_location= '../../../../../../eggs/'
repo_location='../../../../../'

all_eggs=os.listdir(eggs_location)
for egg in all_eggs:
    full_path=eggs_location+egg
    if os.path.isdir(full_path):
        sys.path.append(full_path)
all_repos=os.listdir(repo_location)
for repo in all_repos:
    full_path=repo_location+repo
    if os.path.isdir(full_path):
        sys.path.append(full_path)

sys.path.append('../')

from rhaptos.cnxmlutils.odt2cnxml import transform
from utils import clean_cnxml
from lxml import etree

if(len(sys.argv) != 2):
    print('usage: python generate_valid_cnxml.py file')
    quit()

filename=sys.argv[1]
name, extension = os.path.splitext(filename)
if(extension != '.odt' and extension != '.doc'):
    print('For now I\'m focusing on ODT and DOC files, and that doesn\'t seem to have the .odt or .doc extension')
    quit()

if(extension == '.doc'):
    command = '/usr/bin/soffice --headless --nologo --nofirststartwizard "macro:///Standard.Module1.SaveAsOOO(' + os.getcwd()+'/'+filename + ',' + os.getcwd()+'/'+name+'.odt' + ')"'
    print(command)
    os.system(command)
    filename=name+'.odt'


valid_filename=name+'.cnxml'
tree, files, errors = transform(filename)
cnxml = clean_cnxml(etree.tostring(tree))
output=open(valid_filename,'w')
output.write(cnxml)
output.close()
os.remove(filename)
print('Done. Valid output has been placed in '+valid_filename)

