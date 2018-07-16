#!/usr/bin/python

import re
import sys
import os

class Clipboard_Capture:
    def __init__(self, input_text):
        self.nid_pre = re.compile(r'(n.*[0-9]*?)\|\|.*')
        try:
            self.thruk_text = " ".join([node.encode('utf-8'). rstrip() for node in input_text.split()])
        except UnicodeDecodeError:
            self.thruk_text = " ".join([node.rstrip() for node in input_text.split()])
        self.regex_dict = {"edi_match": re.compile(r'edi-\S* '),
                           "cori_match": re.compile(r'cori-\S* '), 
                           "host_match": re.compile(r'(cori|edi)-\S* '),
                           "nid_match": re.compile(r'.*(nid\d{5}).*'),
                           "reason_match": re.compile(r'.*REASON: (\".*?\").*'),
                           "slurm_match": re.compile(r'.*SLURM: (.*?),.*'),
                           "user_match": re.compile(r'.* USER: (\S*) .*'),
                           "job_match": re.compile(r'.* JOBNUM: (\S*), .*')}
        self.cab_list = [cname for cname in self.thruk_text.split() if cname.startswith('cori') or cname.startswith('edi')]
        self.thruk_text = re.split(self.regex_dict["host_match"], self.thruk_text)
        self.hosts_list = [host for host in self.thruk_text if host == "edi" or host == "cori"]
        self.thruk_text = [entry for entry in self.thruk_text if entry != "" and entry != "edi" and entry != "cori"]
        self.cab_list = [name[4:] if name.startswith('edi') else name[5:] for name in self.cab_list]
        try:
            assert len(self.thruk_text) == len(self.hosts_list) and len(self.hosts_list) == len(self.cab_list)
        except AssertionError:
            print("Regex parsing did not handle output correctly")
            exit()
 
    def json_out(self):
        rd = self.regex_dict
        self.thruk_dict = {'Users':{}}
        for item, host, cab in zip(self.thruk_text, self.hosts_list, self.cab_list):

            #if node is not a match entry, skip
            if not re.match(rd['nid_match'], item):
                continue

            #some Nagios output does not include reason
            if not re.match(rd['reason_match'], item):
                if not re.match(rd['slurm_match'], item):
                    reason = "Null"
                else:
                    reason = re.sub(rd['slurm_match'], r'\1', item)
            else:
                reason = re.sub(rd['reason_match'], r'\1',item)

            temp_dict = {  "User":re.sub(rd['user_match'], r'\1', item),
                           "Node":re.sub(rd['nid_match'], r'\1', item),
			                "Job":re.sub(rd['job_match'], r'\1', item),
			             "Reason":reason,
                          "Cname": cab,
			               "Host": host}

            #account for a user not currently in thruk_dict
            if temp_dict['User'] not in self.thruk_dict['Users']:
                self.thruk_dict['Users'].update(
		          {temp_dict['User']:
		            {"Jobs":
		              {temp_dict['Job']:
			            {"Nodes":
			              {temp_dict['Node']+"||"+temp_dict['Cname']:
			                {"Reason":temp_dict['Reason'],"Host":temp_dict["Host"]}
			              }
                        }
                      }
                    }
                  }
                )
            #If user is added, handle whether or not their job is in their user entry
            else:
                user_ref = self.thruk_dict['Users'][temp_dict['User']]
                job_ref = user_ref['Jobs']
                if temp_dict['Job'] in job_ref:
                    node_ref = job_ref[temp_dict['Job']]['Nodes']
                    node_ref.update({temp_dict['Node']+" | "+temp_dict['Cname']:{"Reason":temp_dict['Reason'],"Host":temp_dict["Host"]}})
                else:
                    job_ref.update(
		              {temp_dict['Job']:
			            {"Nodes":
			              {temp_dict['Node']+"||"+temp_dict['Cname']:
			                {"Reason":temp_dict['Reason'],"Host":temp_dict["Host"]}
			              }
			            }
		              }
		            )
        return self.thruk_dict
    
    def json_to_string(self):
        '''
        Converts json object into a single legible string
        Allows output to be sent back to the GUI as a single object
        '''
        thruk_dict = self.json_out()
        scrape_string = ""
        for user in thruk_dict['Users']:
            scrape_string += '\n'
            scrape_string += 'User: {}'.format(user)+'\n'
            scrape_string += "#"*6+"#"*len(user)+'\n'
            this_user = thruk_dict['Users'][user]
            for jobs in this_user:
                scrape_string += "Jobs"+"\n"
                for job in this_user['Jobs']:
                    scrape_string += ">>>"+job+":"+"\n"
                    node_list = [re.sub(self.nid_pre, r'\1', entry) for
                                 entry in this_user['Jobs'][job]['Nodes']]
                    scrape_string += ">>>>>>>Nodes: "+",".join(node_list)+"\n"
                    for entry in this_user['Jobs'][job]['Nodes']:
                        scrape_string += entry+"\n"
                        scrape_string += str(this_user['Jobs'][job]['Nodes'][entry])+"\n"
        return scrape_string

    def print_json(self):
        '''
        Prints json ojbect(nodes grouped by job_id's, aggregated by users)
        in a legible, line item format.
        '''
        print("\n\n\n")
        thruk_dict = self.json_out()
        for user in thruk_dict['Users']:
            print("\n")
            print("User: "+user)
            print("#"*6+"#"*len(user))
            this_user = thruk_dict['Users'][user]
            #for jobs in this_user:
            print("Jobs:")
            for job in this_user['Jobs']:
                print(">>>"+job+":")
                node_list = [re.sub(self.nid_pre, r'\1', entry) for 
                         entry in this_user['Jobs'][job]['Nodes']]
                print(">>>>>>>Nodes: "+",".join(node_list))
                for entry in this_user['Jobs'][job]['Nodes']:
                    print(entry)
                    print(this_user['Jobs'][job]['Nodes'][entry])

class Live_Capture:
    def __init__(self, master_dict):
        '''
        Methods of this class will handle dictionary objects returned
        by querying the LiveStatus socket
        Slightly reinventing the wheel, but would like to have independent 
        methods for the various parsing sources
        '''
        self.master_dict = master_dict
        self.nid_pre = re.compile(r'(n.*[0-9]*?)\|\|.*')

    def print_json(self):
        for user in self.master_dict['Users']:
            print("\n")
            print("User: "+user)
            print("#"*6+"#"*len(user))
            this_user = self.master_dict['Users'][user]
            for jobs in this_user:
                #print(this_user)
                print("Jobs:")
                for job in this_user['Jobs']:
                    print(">>>"+job+":")
                    node_list = [re.sub(self.nid_pre, r'\1', entry) for 
                                 entry in this_user['Jobs'][job]['Nodes']]
                    print(">>>>>>>Nodes: "+",".join(node_list))
                    for entry in this_user['Jobs'][job]['Nodes']:
                        print(entry)
                        print(this_user['Jobs'][job]['Nodes'][entry])

    def json_string(self, post_console=False):
        '''
        Converts json object into a single legible string
        Allows output to be sent back to the GUI as a single object
        '''
        scrape_string = ""
        for user in self.master_dict['Users']:
            scrape_string += '\n'
            scrape_string += 'User: {}'.format(user)+'\n'
            scrape_string += "#"*6+"#"*len(user)+'\n'
            this_user = self.master_dict['Users'][user]
            for jobs in this_user:
                scrape_string += "Jobs"+"\n"
                for job in this_user['Jobs']:
                    scrape_string += ">>>"+job+":"+"\n"
                    node_list = [re.sub(self.nid_pre, r'\1', entry) for
                                 entry in this_user['Jobs'][job]['Nodes']]
                    scrape_string += ">>>>>>>Nodes: "+",".join(node_list)+"\n\n"
                    for entry in this_user['Jobs'][job]['Nodes']:
                        scrape_string += entry+"\n"
                        if post_console:
                            scrape_string += "*"*len(entry)+"\n"
                            final_level = this_user['Jobs'][job]['Nodes'][entry]
                            scrape_string += "Reason: "+final_level['Reason']+"\n"
                            scrape_string += "-"*7 + "\n"
                            scrape_string += "State: "+final_level['State']+"\n"
                            scrape_string += "-"*6 + "\n"
                            scrape_string += "Date/Time: "+final_level['Date/Time']+"\n"
                            scrape_string += "-"*10 + "\n"
                            scrape_string += "Console Output: " + "\n" + "-"*15 + "\n"
                            scrape_string += "\n".join(final_level['Console'])+"\n\n"
                        else:
                            scrape_string += str(this_user['Jobs'][job]['Nodes'][entry])+"\n"
        return scrape_string
    
if __name__=="__main__":
    '''using test clipboard output'''
    with open('testcb','r') as cb:
        capture = Clipboard_Capture(cb.read())
        capture.print_json()
