#!/usr/bin/python

import socket
import re
import sys
import os

'''Query Commands (using GET method):
   hosts - your Nagios hosts
   services - your Nagios services, joined with all data from hosts
   hostgroups - you Nagios hostgroups
   servicegroups - you Nagios servicegroups
   contactgroups - you Nagios contact groups
   servicesbygroup - all services grouped by service groups
   servicesbyhostgroup - all services grouped by host groups
   hostsbygroup - all hosts group by host groups
   contacts - your Nagios contacts
   commands - your defined Nagios commands
   timeperiods - time period definitions (currently only name and alias)
   downtimes - all scheduled host and service downtimes, joined with data from hosts and services.
   comments - all host and service comments
   log - a transparent access to the nagios logfiles (include archived ones)ones
   status - general performance and status information. This table contains exactly one dataset.
   columns - a complete list of all tables and columns available via Livestatus, including descriptions!
   statehist - 1.2.1i2 sla statistics for hosts and services, joined with data from hosts, services and log.
'''
class QueryLive:
    '''query example:
       ************
       GET services
       Columns: host_name description state
       Filter: state = 2
       Filter: in_notification_period = 1
       ************
    '''
    def __init__(self, alarm_level='Critical'):
        '''
        Initialize a socket connection to LiveStatus endpoint
        Lifespan of connection is good for a single Query
        Afterwards, the object's __init__ method must be called 
        to reactivate a socket connection
        '''
        if socket.gethostname() == 'corimon.nersc.gov':
            socket_path = '/var/nagios/rw/live'
            self.host = 'cori'
        elif socket.gethostname() == 'edimon.nersc.gov':
            socket_path = '/var/spool/nagios/cmd/live'
            self.host = 'edison'
        if alarm_level == 'Critical':
            self.state_level = 2
        elif alarm_level == 'Warning':
            self.state_level = 1
        self.live_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.live_socket.connect(socket_path)

    def query_string(self, testing=False):
        '''
        default arg 'state_level' can be changed to 1 to capture 'warning' alarms
        query_string's default purpose, is to query the socket end point
        for unacknowledged Nagios alarms.
        Changing the default 'testing' argument to True allows for viewing
        of all acknowledged alarms
        '''
        ack_flag = 0
        if testing:
            ack_flag = 1
        query = "GET services\nColumns: "
        query += "acknowledged host_name host_alias "
        query += "state plugin_output comments_with_info\nFilter: "
        query += "state = %s\nFilter: acknowledged = %s\n" %(self.state_level, ack_flag)
        return query
        
    def query_socket(self, query_command):
        '''
        query_socket sends a single query command to the socket end-point
        then immediately shuts down the socket connection
        Returned object is a list of strings containing data per Nagios
        alarm
        '''
        self.live_socket.send(query_command)
        self.live_socket.shutdown(socket.SHUT_WR)
        response = self.live_socket.recv(100000000)
        table = [line.split(';') for line in response.split('\n')[:-1]]
        return table

    def parse_computes(self, testing=False):
        '''
        parse_computes will extract compute nodes from 'query_socket'
        It will minimize query_socket's table output to:
          *node cabinet name
          *node nid-name
          *alarm description (containing user and job number data)
        '''
        if testing: 
            query = self.query_string(testing=True)
        else:
            query = self.query_string()
        compute_list = [node for node in self.query_socket(query) if 'nid' in node[2]]
        #refine the compute list to c-name, nodename, and problem/comment data only
        compute_list = [[node[1], node[2], node[4]] for node in compute_list]
        return compute_list

    def json_master(self, testing=False):
        '''
        json_master will build an aggregated json object
        grouping nodes (hierarchically) by:
            *user->job_id->node_id (listing alarm 'Reason' per node)
        '''
        if testing:
            node_lists = self.parse_computes(testing=True)
        else:
            node_lists = self.parse_computes()
        #for i in node_lists:print(i) ##for testing/troubleshooting
        ##create an empty dictionary, parse node_lists per node and begin grouping data:
        rgx_dct = {   "job_match": re.compile(r'.*JOBNUM: (\S*), .*'),
                     "user_match": re.compile(r'.*USER: (\S*)<.*'),
                   "reason_match": re.compile(r'.*REASON: (\".*?\").*'),
                    "slurm_match": re.compile(r'.*SLURM: (.*?),.*'),
                     "time_match": re.compile(r'.*TIME: (\d.*?),.*')
        } 

        master_dict = {"Users":{}}
        ##isolate comments section and extract user, reason, job_id via regex
        for node in node_lists:
            #Account for missing reasons field:
            if not re.match(rgx_dct['reason_match'], node[2]):
                if not re.match(rgx_dct['slurm_match'], node[2]):
                    reason = "Null"
                    state = "Null"
                else:
                    reason = re.sub(rgx_dct['slurm_match'], r'\1', node[2])
                    state = re.sub(rgx_dct['slurm_match'], r'\1', node[2]) ###break
            else:
                reason = re.sub(rgx_dct['reason_match'], r'\1', node[2])
                if not re.match(rgx_dct['slurm_match'], node[2]):
                    state = "Null"
                else:
                    state = re.sub(rgx_dct['slurm_match'], r'\1', node[2]) ###break 

            #Account for N/A user field:
            if not re.match(rgx_dct['user_match'], node[2]):
                user = "Null"
            else:
                user = re.sub(rgx_dct['user_match'], r'\1', node[2])
            #Account for N/A job_id field:
            if not re.match(rgx_dct['job_match'], node[2]):
                job_id = "Null"
            else:
                job_id = re.sub(rgx_dct['job_match'], r'\1', node[2])  
            #Account for missing time-stamps:
            if not re.match(rgx_dct['time_match'], node[2]):
                date_time = "Null"
            else:
                date_time = re.sub(rgx_dct['time_match'], r'\1', node[2])
                  
            #construct a temporary dictionary of node data:
            temp_dict = {  "C-name": node[0], 
                         "Nid-name": node[1], 
                             "User": user,  
                           "Job_id": job_id,
                           "Reason": reason,
                            "State": state,
                             "Host": self.host,
                        "Date/Time": date_time
            }
            ####for full comment text:
            #temp_dict.update({"Text": node[2]})

            #print(temp_dict) ##show output of individual temp_dicts
            #exit()
            
            if temp_dict['User'] not in master_dict['Users']:
                master_dict['Users'].update(
                  {temp_dict['User']:
                    {'Jobs':
                      {temp_dict['Job_id']:
                        {'Nodes':
                          {temp_dict['Nid-name']+'||'+temp_dict['C-name']:
                            {'Reason':temp_dict['Reason'],
                             'State':temp_dict['State'], 
                             'Host':temp_dict['Host'], 
                             'Date/Time':temp_dict['Date/Time']}
                          }
                        }
                      }
                    }
                  }
                )
            else:
                user_ref = master_dict['Users'][temp_dict['User']]
                job_ref = user_ref['Jobs']
                if temp_dict['Job_id'] in job_ref:
                    node_ref = job_ref[temp_dict['Job_id']]['Nodes']
                    node_ref.update({temp_dict['Nid-name'] +'||'+ temp_dict['C-name']:
                        {    'Reason': temp_dict['Reason'],
                              'State': temp_dict['State'],
                               'Host': temp_dict['Host'],
                          'Date/Time': temp_dict['Date/Time']}
                        })
                else:
                    job_ref.update(
                      {temp_dict['Job_id']:
                        {'Nodes':
                          {temp_dict['Nid-name']+'||'+temp_dict['C-name']:
                            {    'Reason':temp_dict['Reason'],
                                  'State':temp_dict['State'],
                                   'Host':temp_dict['Host'],
                              'Date/Time':temp_dict['Date/Time']
                            }
                          }
                        }
                      }
                    )
        return master_dict
        
    def print_table(self, table_data):
        for line in table_data:
            print(line)
            print('\n')

if __name__ == "__main__":
    #newSocket = QueryLive(alarm_level='Warning')
    newSocket = QueryLive(alarm_level='Critical') #change alarm_level to 'Warning' for warning/level 1
    ###To query unacknowledged nodes, remove the 'testing'=True argument below###
    #print(newSocket.json_master(testing=True))
    print(newSocket.json_master(testing=False)) 
