#!/usr/bin/python

import paramiko,socket, sys, os, re
from subprocess import check_output,Popen,PIPE
from datetime import datetime,date,timedelta
from paramiko import client as pclient

class Remote_Connect:
    def __init__(self, jump_host, remote_host):
        #create an open ssh client
        self.remote_host = remote_host
        self.host_ssh = pclient.SSHClient()
        self.host_ssh.load_system_host_keys()
        self.host_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.host_ssh.connect(jump_host, username='root')

    def remote_command(self, command):
        stdin, stdout, stderr = self.host_ssh.exec_command(command)
        outlines = " ".join(stdout.readlines())
        return outlines

    def file_transport(self, query_file):
        if socket.gethostname() == 'jamesmac':
            abs_path = "/Users/jdillon/Desktop/sretools/PyTools/Thruk_Scrape/"
        else:
            abs_path = "/Users/operator/james_dir/Development/sretools/PyTools/Thruk_Scrape/"
        jump_destination = '/tmp/{}'.format(query_file)
        if self.remote_host.startswith('corimon'):
            remote_destination = '/var/nagios/rw'
        elif self.remote_host.startswith('edimon'):
            remote_destination = '/var/spool/nagios/cmd'
        sftp = self.host_ssh.open_sftp()
        #place file on jump host
        sftp.put(abs_path+query_file, jump_destination)
        self.remote_command('scp /tmp/{} {}:{}'.format(query_file, self.remote_host, remote_destination))
        #remove the file from jump host
        self.remote_command('rm /tmp/{}'.format(query_file))
        self.remote_command('ssh {} chmod 777 {}/{}'.format(self.remote_host, remote_destination, query_file))
        sftp.close()
        stdout = (self.remote_command('ssh {} python {}/{}'.format(self.remote_host, remote_destination, query_file)))
        #remove the file from the remove host
        self.remote_command('ssh {} rm {}/{}'.format(self.remote_host, remote_destination, query_file))
        return stdout    

    def con_shutdown(self):
        self.host_ssh.close()

if __name__=="__main__":
    corimon_con = Remote_Connect('bochy.nersc.gov', 'corimon.nersc.gov')
    cori_out = corimon_con.file_transport('liveQuery.py')
    corimon_con.con_shutdown()
    print(cori_out)
    edimon_con = Remote_Connect('bochy.nersc.gov', 'edimon.nersc.gov')
    edi_out = edimon_con.file_transport('liveQuery.py')
    edimon_con.con_shutdown()
    print(edi_out)
