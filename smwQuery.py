#!/usr/bin/python

import paramiko, socket, subprocess, datetime, sys, os, re
from subprocess import check_output,Popen,PIPE
from paramiko import client as pclient

class Console_Parse:
    def __init__(self, host, username, password="None"):
        self.color_dir = {
            "none":"\033[0m",
            "neogreen_text":"\033[38;5;82m",
            "fuchsia_text":"\033[38;5;13m",
            "orchid_text":"\033[38;5;212m",
            "green_bak":"\033[48;5;119m",
            "turq_bak":"\033[48;5;87m",
            "d_pink_bak":"\033[48;5;197m"
        }
        self.username = username
        self.password = password
        self.host = host #must be either corismw || edismw
        self.console_master = self.master_list(yesterday=False)

    def master_list(self, tail=True, tail_lines=50000, yesterday=False):
        '''
        Grab the target day's console log from the SMW
        '''
        strf = datetime.datetime.strftime
        if yesterday:
            now_string = strf(datetime.datetime.now() -
                         datetime.timedelta(days=1),"%Y%m%d")
        else:
            now_string = strf(datetime.datetime.now(),"%Y%m%d")
        #create our remote command to be run on the smw
        if tail: #by default, we are tailing the last 500 lines of the console log 
            con_out = "tail -n {} /var/opt/cray/".format(tail_lines)
        else: #by setting 'tail' to false we cat the entire console log
            con_out = "cat /var/opt/cray/"
        con_out += "disk/1/log/p0-current/"
        con_out += "console-{}".format(now_string)
        remote_com = "ssh {}@sg-crt ssh root@{} ".format(self.username, self.host)
        remote_com += "{}".format(con_out)
        remote_proc = subprocess.Popen(remote_com, stdout=subprocess.PIPE, shell=True)
        (stdout, stderr) = remote_proc.communicate()
        if not stdout:
            if stderr:
                stderr = [line for line in stderr.split('\n') if line != '']
                return stderr
            else:
                return ''    
        stdout = [line for line in stdout.split('\n') if line != '']
        return stdout

    def console_list(self, c_name):
        '''
        Method will parse smw's console log, returning a list
        pertaining to an individual node (dictated by c-name arg)
        -If default arg yesterday is changed to True: 
          *Yesterday's console log will be parsed
          *This is mainly useful, for gathering logs immediately
           switch from PM -> AM.
        '''
        #create our subprocess pipe and execute command remotely
        console_cmatch = [line for line in self.console_master if c_name in line]
        if console_cmatch:
            return console_cmatch
        else:
            return ''
                
    def trim_console(self, console_lines, printing=True, pre_lines=5, post_lines=100):
        '''
        Method will display gathered console log lines to stdout
        Mainly used for testing, or when run in CLI version of prog
        -Pre_lines arg indicates how many lines preceding the 
         first instance of a log line with a prolog notification
         should be included in output.
        -Post_lines arg indicates how many lines following the
         last instance of a log line (pertaining to the node)
         with a 'prolog' notification should be included in
         output as a maximum cap.
        Method returns a stripped down version of the nid's console log output
        based on application of default arguments
        '''
        prolog_indices = []
        for index, line in enumerate(console_lines):
            if 'prolog' in line:
                prolog_indices.append(index)
        if prolog_indices:
            if prolog_indices[-1] > pre_lines:
                index_start = prolog_indices[-1] - 5
            else:
                index_start = prolog_indices[-1]
            if len(console_lines[index_start:]) >= post_lines: #change int to variable `post lines`
                #trim the line output: 5 lines before last 'prolog', 10 lines after:
                console_lines = console_lines[index_start-pre_lines:index_start+post_lines]
            else:
                console_lines = console_lines[index_start:]
            if printing:
                for line in console_lines:
                    if 'prolog' in line:
                        print("{}{}{}{}".format(
                            self.color_dir['turq_bak'],
                            self.color_dir['orchid_text'],
                            line,
                            self.color_dir['none']
                        ))    
                    else:
                        print(line)
        else:
            console_lines = console_lines[-1*(pre_lines+post_lines):]
            if printing:
                for line in console_lines:
                    print(line)
        return console_lines

if __name__=="__main__":
    if len(sys.argv) < 4:
        for i in range(4):
            print("*"*80)
        print("Incorrect argument usage:")
        print("hostname, username, c-name = sys.argv[1], sys.argv[2], sys.argv[3]")
        for i in range(4):
            print("*"*80)
        exit()
    hostname, username, c_name = sys.argv[1], sys.argv[2], sys.argv[3] 
    cp = Console_Parse(hostname, username)
    #console_list method retrieves all console log lines per c_name
    #trim_console method prints trimmed console log to stdout, but also returns list of lines
    cp.trim_console(cp.console_list(c_name)) 
