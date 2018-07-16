#!/usr/bin/python

import json, getpass
from liveTunnel import *
from gui_gen import * #gui_gen contains both classes in cb_parse (Live_Capture:lc, Clipboard_Capture:cb)
from gui_gen import Thruk_Scrape, Menu_Prompt, Lq_Display
from smwQuery import *
from smwQuery import Console_Parse
from mfaLoad import *
from mfaLoad import Load_MFA
from liveTunnel import Remote_Connect as Rc

class Main:
    def __init__(self, username, nagios_box):
        #nagios_box must be either 'corimon.nersc.gov' || 'edimon.nersc.gov'
        self.nagios_box = nagios_box
        self.nid_sub = re.compile(r'n.*-([ec].*\d)')
        self.hostname = ''
        self.username = username
        self.connections = []

    def host_query(self):
        remote_con = Rc('bochy.nersc.gov', self.nagios_box)
        remote_out = eval(remote_con.file_transport('liveQuery.py'))
        remote_con.con_shutdown()
        remote_live = lc(remote_out) #remote_live.master_dict exports the host's json obj
        return remote_live

    def console_update(self, remote_instance):
        #injects console data into return value of host_query's master_dict parameter
        if self.nagios_box == 'corimon.nersc.gov':
            smw_host = 'corismw'
        elif self.nagios_box == 'edimon.nersc.gov':
            smw_host = 'edismw'
        else:
            print("Not a recognized host option, exiting")
            exit()
        cp = Console_Parse(smw_host, self.username)
        user_level = remote_instance.master_dict['Users']
        for user in user_level:
            jobs_level = user_level[user]['Jobs']
            for job in jobs_level:
                nodes_level = jobs_level[job]['Nodes']
                for nodes in nodes_level:
                    c_name = re.sub(self.nid_sub, r'\1', nodes)
                    for i in range(2):
                        nodes_level[nodes].update({"Console":cp.trim_console(cp.console_list(c_name), 
                                                                             printing=False)})
        return remote_instance

    def load_mfa(self):
        '''
        calls mfaLoad's Load_MFA class
        and load's the operator's credentials
        into the ~/.ssh directory
        '''
        pword = getpass.getpass("Please enter your mfa-key password: ")
        child = Load_MFA()
        child.connect(self.username, 'sg-crt', pword)

    def pre_console(self):
        #this function will allow operators without creds to get output
        #and aggregate data for downed nodes (w/ no console log output)
        pass        

    def post_console(self):
        #call the console update method on returned master dict from host_query()
        #this will inject console log data into the json object
        json_console = self.console_update(self.host_query())
        print(json_console.json_string(post_console=True))
        

if __name__=="__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '-l':
        if sys.version_info[0] == 3: raw_input = input
        uname = raw_input("Please enter your sg username: ")
        
        Cori_main = Main(uname, 'corimon.nersc.gov')
        Cori_main.load_mfa()
        Cori_main.post_console()
        ########################
        Edi_main = Main(uname,'edimon.nersc.gov')
        Edi_main.post_console()

    else:
        #GUI run versin of the program
        ts = Menu_Prompt()
        ts.menu_gui.mainloop()
