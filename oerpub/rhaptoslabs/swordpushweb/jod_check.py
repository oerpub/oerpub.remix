#! /usr/bin/python
'''
Author: Gbenga Badipe

Requires: A Process name 

Effects: Returns true if the process is running, otherwise returns false. 
		 Except in the case in which it's the oOo process that is being checked.
		 If it is then it starts the process and returns true
'''
import subprocess
import sys

def check(process_name):
	#Calls netstat command and pipes output to the grep process to check to see if JOD is running
	ps_process = subprocess.Popen(["netstat"], stdout = subprocess.PIPE)
	grep_process = subprocess.Popen(["grep", process_name], stdin=ps_process.stdout, stdout = subprocess.PIPE)
	output = grep_process.communicate()[0]
	ps_process.stdout.close() #In case the grep process exits befor ps; assures that ps receives a SIGPIPE
	
	#If the process is not there then return false otherwise
	if (output == None or output == ""):
		return False
	else:
		return True	
