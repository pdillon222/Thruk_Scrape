#!/usr/bin/python

import threading, socket, pexpect, time, sys, os, re


class Load_MFA:
    '''Load User's MFA Token Into .ssh Directory:

    Methods of this class will allow the operator's MFA token
    and ssh credentials to be programatically located into 
    the .ssh directory.
    This will allow the operator to later query the smw hosts
    via either of the sg servers as a jump host.
    '''

    def __init__(self):
        self.enter_prompt = "Enter.*"

    def out_none(self, stream):
        return ""
    
    def interact(self, child_proc):
        child_proc.interact(output_filter=self.out_none)
 
    def sendline(self, child_proc):
        child_proc.sendline('exit')
        #child_proc.kill(9)
        #child_proc.close(force=True)

    def connect(self, user, host, password):
        if socket.gethostname() == 'crt-vid3':
            sshpath = '/Users/operator/.ssh/'
        else:
            sshpath = '/Users/{}/.ssh/sockets/'.format(user)

        ret = os.system("ls -l /Users/operator/.ssh/master-jdillon@sg-crt.nersc.gov:23 >> /dev/null 2>&1")
        sshpath += 'master-{}@sg-crt.nersc.gov:22'.format(user)
        retval = os.system('ls -l {} >> /dev/null 2>&1'.format(sshpath))
        #this is a workaround test, to see if socket already exists
        #If so, the sg key is loaded and there is no need to proceed
        if retval == 0: #break out and stop load attempts 
            return
        connStr = 'ssh {}@{}'.format(user, host)
        child = pexpect.spawn(connStr, timeout=10)
        match = child.expect([self.enter_prompt, pexpect.EOF, pexpect.TIMEOUT], timeout=-1)
  
        if match == 0:
            '''
            Indicates that the sg-prompt has been matched
            Will send the operator's password, and start thread launching a temporary interactive
            shell open to the sg host.
            Will then start a second thread to send an exit command to the temporary interactive 
            session.  Once this is accomplished, the operator's credentials have been loaded.
            '''
            child.sendline(password)
            #perhaps create another child.expect statement here, to catch incorrect password input
            interaction = threading.Thread(name="start_interactive", target=self.interact, args=(child, ))
            sendkill = threading.Thread(name="kill_child", target=self.sendline, args=(child, ))
            interaction.start()
            sendkill.start()
            interaction.join()
            sendkill.join()
            child.terminate(force=True)
            return 0
        
        elif match == 1:
            '''
            Indicates an either a password issue, or missing MFA
            Returns error exit code '1' 
            '''
            print("MFA key not inserted, or password rejected")
            return 1

        elif match == 2:
            '''
            A timeout likely indicates a previously loaded ssh credential
            Recursively call the function to reload the time-stamp on the credential
            '''
            #print("host key previously loaded, re-loading")
            #if file exists below:
            #os.system('rm ~/.ssh/sockets/master-{}@sg-crt.nersc.gov:22'.format(user))
            #child = self.connect(user, host, password) 
            #print("causing timeout")
            return 2

if __name__=="__main__":

    user = 'jdillon'
    host = 'sg-crt'
    password = ''   
    child = Load_MFA()
    child.connect(user, host, password)
