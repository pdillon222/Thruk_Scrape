#!/usr/bin/python

from cb_parse import Clipboard_Capture as cb
from cb_parse import Live_Capture as lc
from mfaLoad import *
from smwQuery import *
from smwQuery import Console_Parse
from mfaLoad import Load_MFA
import sys
if sys.version_info[0] == 3:
    from tkinter import *
    pyversion = 3
else:
    from Tkinter import *
    pyversion = 2
import json
from liveTunnel import *
from liveTunnel import Remote_Connect as Rc
import re
import os

###################################################################################
##                                     GLOBALS:                                  ##
##                -`pyversion` declared upon [tT]kinter import                   ##
##                  * denotes python version per host                            ## 
##                                                                               ##
###################################################################################


###################################################################################
##                                   END GLOBALS                                 ##
###################################################################################
       
class Thruk_Scrape:
    '''
    class contains methods to be used for capturing
    and parsing data from the Thruk web interface
    Allows a user to selectively target alarms 
    currently displayed in Thruk
    '''
    def __init__(self):
        self.thruk_capture = Tk()
        self.dims = self.dimension_calc()
        self.thruk_capture.geometry(self.dims['dims']) 
        self.thruk_capture.maxsize(self.dims['width'], self.dims['height'])
        self.entry_widget_width = self.dims['entry_width']
        self.entry_widget_height = self.dims['entry_height']
        #Defining the Frame 'input_gui'
        self.input_gui = Frame(self.thruk_capture, bg='SlateGray2')
        self.input_gui.grid()
        ######################
        self.create_widgets()

    def dimension_calc(self):
        '''
        Differing screen resolution can wreak havoc on 
        static Tk frame dimensions.  This method will
        allow for troubleshooting of alternate monitor 
        sizes and aspect ratios.
        '''
        root = self.thruk_capture
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        if screen_height > 901 and screen_width > 1401:
            FRAME_HEIGHT = 795
            FRAME_WIDTH = 900 
            ENTRY_WIDTH = 94
            ENTRY_HEIGHT = 48
        else:
            FRAME_HEIGHT = 800
            FRAME_WIDTH = 770
            ENTRY_WIDTH = 80
            ENTRY_HEIGHT = 40 

        FRAME_DIMS = '{}x{}'.format(FRAME_WIDTH,
                                    FRAME_HEIGHT)
        dim_dir = {'height': FRAME_HEIGHT,
                    'width': FRAME_WIDTH,
             'entry_height': ENTRY_HEIGHT,
              'entry_width': ENTRY_WIDTH,      
                     'dims': FRAME_DIMS
                  }
        return dim_dir
    
    def create_widgets(self):
        self.input_gui.label = Label(self.thruk_capture, text='Thruk Output')
        self.input_gui.label.grid(row=0, column=1, pady=5)
        self.input_gui.entry = Text(self.thruk_capture, 
                                    bd=5, 
                                    width=self.entry_widget_width, 
                                    height=self.entry_widget_height,
                                    relief=SUNKEN, 
                                    insertbackground="white",
                                    background="black", 
                                    fg="white", 
                                    font=30)
        self.input_gui.entry.grid(row=1, column=1, pady=5)

        #Scrollbar: attatch to Text
        self.scrollbar = Scrollbar(self.thruk_capture, command=self.input_gui.entry.yview)
        self.scrollbar.grid(row=1, column=2, sticky='nsew')
        self.input_gui.entry['yscrollcommand'] = self.scrollbar.set

        #Button: capture text
        self.input_gui.button = Button(self.thruk_capture, text='Enter Input')
        self.input_gui.button['command'] = lambda: self.text_capture()
        self.input_gui.button.grid(row=4, column=1, pady=5)

        #Button: kill gui session
        self.input_gui.button = Button(self.thruk_capture, text='Quit')
        self.input_gui.button['command'] = lambda: self.kill_all()
        self.input_gui.button.grid(row=5, column=1, pady=5)
 
    def text_capture(self):
        clipboard_text = self.input_gui.entry.get("1.0",END)
        #Delete display & call the parser function on clipboard_text
        capture = cb(clipboard_text)
        self.input_gui.entry.delete(1.0, END)
        self.input_gui.entry.insert(1.0, capture.json_to_string()) #inherited function called here)

    def kill_all(self):
        self.thruk_capture.destroy()

class Lq_Display:
    '''
    class creates a GUI for displaying unacknowledged critical compute nodes
    the method queries the LiveStatus socket end-point directly
    Thus, the GUI will display every 'Critical' alarming compute node
    that has yet to be acknowledged.
    Nodes are grouped by user, and sub-grouped by job_id
    '''
    def __init__(self):
        self.thruk_capture = Tk()
        self.dims = self.dimension_calc()
        self.thruk_capture.geometry(self.dims['dims'])
        self.thruk_capture.maxsize(self.dims['width'], self.dims['height'])
        self.entry_widget_width = self.dims['entry_width']
        self.entry_widget_height = self.dims['entry_height']
        #Defining the Frame 'input_gui'
        self.input_gui = Frame(self.thruk_capture, bg='SlateGray2')
        self.input_gui.grid()
        ######################
        self.cori_master = None
        self.edi_master = None
        self.username = ''
        self.nid_sub = re.compile(r'n.*-([ec].*\d)')
        self.create_widgets()

    def load_mfa(self, username, pword):
        child = Load_MFA()
        child.connect(username, 'sg-crt', pword)

    def dimension_calc(self):
        '''
        Differing screen resolution can wreak havoc on
        static Tk frame dimensions.  This method will
        allow for troubleshooting of alternate monitor
        sizes and aspect ratios.
        '''
        root = self.thruk_capture
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        if screen_height > 901 and screen_width > 1401:
            FRAME_HEIGHT = 1020
            FRAME_WIDTH = 1240
            ENTRY_WIDTH = 150
            ENTRY_HEIGHT = 48
        else:
            FRAME_HEIGHT = 800
            FRAME_WIDTH = 950
            ENTRY_WIDTH = 114
            ENTRY_HEIGHT = 35

        FRAME_DIMS = '{}x{}'.format(FRAME_WIDTH,
                                    FRAME_HEIGHT)
        dim_dir = {'height': FRAME_HEIGHT,
                    'width': FRAME_WIDTH,
             'entry_height': ENTRY_HEIGHT,
              'entry_width': ENTRY_WIDTH,
                     'dims': FRAME_DIMS
                  }
        return dim_dir

    def create_widgets(self):
        self.input_gui.label = Label(self.thruk_capture, text='Critical Unacknowledged Compute Nodes:')
        self.input_gui.label.grid(row=0, column=1, pady=5)
        self.input_gui.entry = Text(self.thruk_capture, 
                                    bd=5, 
                                    width=self.entry_widget_width, 
                                    height=self.entry_widget_height,
                                    relief=SUNKEN, 
                                    insertbackground="white",
                                    background="black", 
                                    fg="white", 
                                    font=30)
        self.input_gui.entry.grid(row=1, column=1, pady=5)

        #Scrollbar: attatch to Text
        self.scrollbar = Scrollbar(self.thruk_capture, command=self.input_gui.entry.yview)
        self.scrollbar.grid(row=1, column=2, sticky='nsew')
        self.input_gui.entry['yscrollcommand'] = self.scrollbar.set

        #Button: capture text
        self.input_gui.capturebutton = Button(self.thruk_capture, text='Display Data')
        self.input_gui.capturebutton['command'] = lambda: self.text_capture()
        self.input_gui.capturebutton.grid(row=4, column=1, pady=5)

        #Button: kill gui session
        self.input_gui.killbutton = Button(self.thruk_capture, text='Quit')
        self.input_gui.killbutton['command'] = lambda: self.kill_all()
        self.input_gui.killbutton.grid(row=5, column=1, pady=5)

    def text_capture(self):
        corimon_con = Rc('bochy.nersc.gov', 'corimon.nersc.gov')
        cori_out = eval(corimon_con.file_transport('liveQuery.py'))
        corimon_con.con_shutdown()
        cori_live = lc(cori_out) #cori_live.master_dict becomes the main json object
        #if the cori master json object has data, add it to the instance per cori
        if cori_live.master_dict['Users']:
            self.cori_master = cori_live  

        edimon_con = Rc('bochy.nersc.gov', 'edimon.nersc.gov')
        edi_out = eval(edimon_con.file_transport('liveQuery.py'))
        edimon_con.con_shutdown()
        edi_live = lc(edi_out) #edi_live.master_dict becomes the main json object
        #if the edison master json object has data, add it to the instance per edison
        if edi_live.master_dict['Users']:
            self.edi_master = edi_live

        ###join the output strings and send to the GUI display
        query_result = cori_live.json_string() + "\n" + edi_live.json_string()
        #query_result += "\n" + str(self.cori_master_json) + "\n" + str(self.edi_master_json)
        self.input_gui.entry.delete(1.0, END)
        self.input_gui.entry.insert(1.0, query_result) #will join edi and cori captured output

        #repopulate sections of the gui:
        ##remove the capture button
        self.input_gui.capturebutton.destroy()
        ##add a prompt button for displaying console lines per node
        self.input_gui.console_button = Button(self.thruk_capture, text='Display Console Data for Nodes?')
        self.input_gui.console_button['command'] = lambda: self.console_push()
        self.input_gui.console_button.grid(row=4, column=1, pady=5)
   
    def console_push(self):
        '''
        Activated once the console button has been presed
        '''
        self.input_gui.killbutton.destroy()
        self.input_gui.console_button.destroy()
        #username label
        self.input_gui.unamelabel = Label(self.thruk_capture, text='//Enter Username:')
        self.input_gui.unamelabel.grid(row=3, column=1, pady=5)
        #username entry box 
        self.input_gui.username = Entry(self.thruk_capture,
                                        bd=5,
                                        width=14,
                                        #height=1,
                                        relief=SUNKEN,
                                        insertbackground="white",
                                        background="black",
                                        fg="white", 
                                        font=30)
        self.input_gui.username.grid(row=4,column=1, pady=2)
        #password label
        self.input_gui.pwordlabel = Label(self.thruk_capture, text='//Enter Password:')
        self.input_gui.pwordlabel.grid(row=5, column=1, pady=2)        
        #password entry box
        self.input_gui.password = Entry(self.thruk_capture,
                                        bd=5,
                                        width=14,
                                        #height=1,
                                        relief=SUNKEN,
                                        show="*",
                                        insertbackground="white",
                                        background="black",
                                        fg="white",
                                        font=30)
        self.input_gui.password.grid(row=6,column=1, pady=2)
        #enter data button
        self.input_gui.enterbutton = Button(self.thruk_capture, text='Enter Info')
        self.input_gui.enterbutton['command'] = lambda: self.console_update() #this will call self.console_update()
        self.input_gui.enterbutton.grid(row=7, column=1, pady=2)

    def console_update(self):
        '''
        Activated once user enters username, password and presses 'Enter Info' button
        Clears the main Text window, and begins running console injection function
        '''
        #we already have access to the lc instances
        #if self.cori_master: inject console info into cori instance, print new json to string
        #if self.edi_master: inject console info into edi instance, print new json to string
        #for reference, look at how this is being handled in the main function
        #get username and password from the new entry boxes
        #[ ] load the user's host keys
        #[ ] clear the main entry GUI
        #[ ] instantiate a console_update for both hosts
        #[ ] process the console update function for both instances
        #[ ] reload the entry GUI
        self.username = self.input_gui.username.get()
        pword = self.input_gui.password.get()
        self.input_gui.username.delete(0, END)
        self.input_gui.password.delete(0, END)
        #correct methods for Text delet
        #self.input_gui.entry.delete(1.0, END)
        #self.input_gui.entry.insert(1.0, capture.json_to_string())
        self.input_gui.entry.delete(1.0, END)
        self.load_mfa(self.username, pword)
        entry_output = ''
        if self.cori_master:
            entry_output += "\n" + self.console_inject(self.cori_master, 'corimon.nersc.gov')
        if self.edi_master:
            entry_output += "\n" + self.console_inject(self.edi_master, 'edimon.nersc.gov')
        self.input_gui.entry.insert(1.0, entry_output)

    def console_inject(self, remote_instance, nagios_box):
        #injects console data into return value of host_query's master_dict parameter
        #nagios box must be named explicitly
        if nagios_box == 'corimon.nersc.gov':
            smw_host = 'corismw'
        elif nagios_box == 'edimon.nersc.gov':
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
        #return updated remote_instance
        #the question then becomes: return the instance or process it's updated json as a string    
        return remote_instance.json_string(post_console=True) 

    def kill_all(self):
        self.thruk_capture.destroy()

class Menu_Prompt:
    '''
    class serves as the initial launch point
    allowing the user to choose whether to 
    query the LiveStatus socket end-point
    or to input clipboard copied data from 
    the Thruk web interface
    '''
    def __init__(self):
        self.launch_menu = Tk()
        self.launch_menu.resizable(0, 0)
        self.launch_menu.geometry('395x347')
        #defining the Frame 'menu_gui'
        self.menu_gui = Frame(self.launch_menu, bg='SlateGray2')
        self.menu_gui.grid()
        ####################
        self.prog_num = IntVar()
        self.menu_widgets()

    def menu_widgets(self):
        self.menu_gui.label = Label(self.launch_menu, text='Please Select an Option:', font=("Courier", 20))
        self.menu_gui.label.grid(row=0, column=1, pady=5)
        #define radio buttons
        prog_options = [("Query the LiveStatus socket endpoint directly", 0),
                        ("Input copied text from the Thruk web interface", 1)]
        self.prog_num.set(0) 
        for val, option in enumerate(prog_options):
            Radiobutton(self.launch_menu,
                        indicatoron=1,
                        text=option[0],
                        padx=20,
                        relief=SUNKEN,
                        justify=CENTER,
                        variable=self.prog_num,
                        command=self.get_option,
                        value=val).grid(row=val+1,
                                        column=1, 
                                        pady=5, 
                                        padx=10, 
                                        sticky=W+S)
        #Button: capture radio selection and launch new GUI
        self.menu_gui.button = Button(self.launch_menu, text='Launch')
        self.menu_gui.button['command'] = lambda: self.option_select()
        self.menu_gui.button.grid(row=3, column=1, pady=5)
        #Button: quit the program cleanly
        self.menu_gui.button = Button(self.launch_menu, text='Quit')
        self.menu_gui.button['command'] = lambda: self.kill_all()
        self.menu_gui.button.grid(row=4, column=1, pady=5)

    def option_select(self):
        if not self.get_option():
            self.kill_all()
            '''Believe the section below was simply sleep-deprived copy pasted, is redundant, waiting and testing for now
            corimon_con = Rc('bochy.nersc.gov', 'corimon.nersc.gov')
            cori_out = eval(corimon_con.file_transport('liveQuery.py'))
            corimon_con.con_shutdown()
            cori_live = lc(cori_out) #cori_live.master_dict becomes the main json object

            edimon_con = Rc('bochy.nersc.gov', 'edimon.nersc.gov')
            edi_out = eval(edimon_con.file_transport('liveQuery.py'))
            edimon_con.con_shutdown()
            edi_live = lc(edi_out) #edi_live.master_dict becomes the main json object
             
            ###join the output strings and send to the GUI display
            query_result = cori_live.json_string() + "\n" + edi_live.json_string()            
            '''
            lq = Lq_Display()
            lq.input_gui.mainloop()
        else:
            self.kill_all()
            ts = Thruk_Scrape()
            ts.input_gui.mainloop()

    def get_option(self):
        return self.prog_num.get() 

    def kill_all(self):
        self.launch_menu.destroy()

if __name__=="__main__":
    mp = Menu_Prompt()
    mp.menu_gui.mainloop()
