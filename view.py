import os, re, itertools
from datetime import datetime, timedelta
from functools import partial

from tkinter import Label, Entry, Button, StringVar, Text, Scrollbar
from tkinter.filedialog import askopenfilenames
from tkinter import tix, ttk, messagebox

CURR_DIR = os.getcwd()
ASSET_DIR = os.path.join(CURR_DIR, 'assets')

class Application(tix.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.options, self.wigets, self.observers = {}, {}, {}

        self.reset_options()
        self.pack()

        self.config_window()
        self.create_widgets()
        self.position_widgets()
    
    def on(self, event, callback):
        assert(event in ('do_roll_marking', 'do_cropping', 'do_training'))
        self.observers[event] = callback

    def reset_options(self):
        self.options = {
            'startTime': None,
            'memList': None,
            'beginSnapshot': tuple(),
            'endSnapshot': tuple(),
            'savePath': os.path.join(CURR_DIR, '考勤结果/')
        }
    
    def reset_ui(self):
        self.widgets['beginEnt']['content'].set('')
        self.widgets['endEnt']['content'].set('')
    
    def log(self, message):
        self.widgets['logPanel'].insert(tix.END, message + os.linesep)

    def config_window(self):
        self.master.title('研讨班辅助考勤')
        self.master.maxsize(650, 330)
        self.master.minsize(650, 330)

    def build_string_var(self, text):
        strVar = StringVar()
        strVar.set(text)
        return strVar

    def create_widgets(self):
        now = datetime.now()
        ocrf = tix.Frame(self)
        trainf = tix.Frame(self)
        sepf = tix.Frame(self)

        ###############
        # OCR Section #
        ###############
        # setup start checking time
        startTimeVar = self.build_string_var(now.strftime('%Y-%m-%d %H:%M:00'))
        startTimeLabel = Label(ocrf, text='当前时间')
        startTimeEnt = Entry(ocrf, textvariable=startTimeVar, width=30)

        # member list file select
        defaultSheet = os.path.join(ASSET_DIR, '考勤初表.xlsx')
        memListVar = self.build_string_var(defaultSheet if os.path.exists(defaultSheet) else '')
        memListLabel = Label(ocrf, text='考勤初表')
        memListEnt = Entry(ocrf, textvariable=memListVar, width=30)
        memListBtn = Button(ocrf, text='选择文件', command=partial(self.select_multi_files, memListVar))

        # attendance snapshots
        beginVar, endVar = self.build_string_var(''), self.build_string_var('')
        beginLabel, endLabel = Label(ocrf, text='首次截图'), Label(ocrf, text='结束截图')
        beginEnt, endEnt = Entry(ocrf, textvariable=beginVar, width=30), Entry(ocrf, textvariable=endVar, width=30)
        beginBtn = Button(ocrf, text='添加文件', command=self.select_screenshots(is_begin=True))
        endBtn = Button(ocrf, text='添加文件', command=self.select_screenshots(is_begin=False))

        # submit button
        submitBtn = Button(ocrf,
            text="自动考勤",
            command=self.on_start_marking)
        
        ttk.Separator(sepf, orient=tix.HORIZONTAL).grid(row=0, columnspan=3, sticky='EW', pady=10)

        ####################
        # Training Section #
        ####################
        trainPicVar, lookupVar = self.build_string_var(''), self.build_string_var('')
        trainPicLabel, lookupLabel = Label(trainf, text='训练图片'), Label(trainf, text='查找表')
        trainPicEnt, lookupEnt = Entry(trainf, textvariable=trainPicVar, width=30), Entry(trainf, textvariable=lookupVar, width=30)
        trainPicBtn = Button(trainf, text='添加文件', command=partial(self.select_multi_files, trainPicVar))
        lookupBtn = Button(trainf, text='添加文件', command=partial(self.select_multi_files, lookupVar))
        
        cropBtn = Button(trainf, text='析取名片', width=13, command=self.on_start_cropping)
        trainBtn = Button(trainf, text='开始训练', width=13, command=self.on_start_training)

        ocrf.grid(sticky='N'), sepf.grid(sticky='N'), trainf.grid(sticky='N')

        self.widgets = {
            'startTimeLabel': startTimeLabel,
            'startTimeEnt': { 'self': startTimeEnt, 'content': startTimeVar },
            'memListLabel': memListLabel, 'memListBtn': memListBtn,
            'memListEnt': { 'self': memListEnt, 'content': memListVar},
            'beginLabel': beginLabel, 'beginBtn': beginBtn,
            'beginEnt': { 'self': beginEnt, 'content': beginVar},
            'endLabel': endLabel, 'endBtn': endBtn,
            'endEnt': { 'self': endEnt, 'content': endVar},
            'submitBtn': submitBtn,
            'logPanel': Text(self),
            'trainPicLabel': trainPicLabel, 'trainPicBtn': trainPicBtn,
            'trainPicEnt': { 'self': trainPicEnt, 'content': trainPicVar},
            'lookupLabel': lookupLabel, 'lookupBtn': lookupBtn,
            'lookupEnt': { 'self': lookupEnt, 'content': lookupVar},
            'cropBtn': cropBtn, 'trainBtn': trainBtn
        }

    def position_widgets(self):
        w = self.widgets # aliasing

        w['startTimeLabel'].grid(row=0, column=0, sticky='W', pady=2)
        w['startTimeEnt']['self'].grid(row=0, column=1,  sticky='W', pady=2)

        w['memListLabel'].grid(row=1, column=0, sticky='W', pady=2)
        w['memListEnt']['self'].grid(row=1, column=1, sticky='W', pady=2)
        w['memListBtn'].grid(row=1, column=2, sticky='W', pady=2, padx=10)

        w['beginLabel'].grid(row=2, column=0, sticky='W', pady=2)
        w['beginEnt']['self'].grid(row=2, column=1, sticky='W', pady=2)
        w['beginBtn'].grid(row=2, column=2, sticky='W', pady=2, padx=10)

        w['endLabel'].grid(row=3, column=0, sticky='W', pady=2)
        w['endEnt']['self'].grid(row=3, column=1, sticky='W', pady=2)
        w['endBtn'].grid(row=3, column=2, sticky='W', pady=2, padx=10)

        w['submitBtn'].grid(row=4, column=1, sticky='we')
        w['logPanel'].grid(row=0, column=3, columnspan=2, rowspan=9, sticky='nsew')

        w['trainPicLabel'].grid(row=0, column=0, sticky='W', pady=2)
        w['trainPicEnt']['self'].grid(row=0, column=1, columnspan=2, sticky='W', pady=2)
        w['trainPicBtn'].grid(row=0, column=3, sticky='W', pady=2, padx=10)

        w['lookupLabel'].grid(row=1, column=0, sticky='W', pady=2)
        w['lookupEnt']['self'].grid(row=1, column=1, columnspan=2, sticky='W', pady=2)
        w['lookupBtn'].grid(row=1, column=3, sticky='W', pady=2, padx=10)

        w['cropBtn'].grid(row=2, column=1, sticky='W')
        w['trainBtn'].grid(row=2, column=2, sticky='W')
        
    def select_multi_files(self, entryVar):
        filepath = askopenfilenames(initialdir=CURR_DIR)
        entryVar.set(filepath)

    def select_screenshots(self, is_begin=True):
        def handler():
            # get data and affected entities
            files = askopenfilenames(initialdir=CURR_DIR)
            if not files: return

            widgetName = 'beginEnt' if is_begin else 'endEnt'
            optName = 'beginSnapshot' if is_begin else 'endSnapshot'
            widgetContent = self.widgets[widgetName]['content']

            # update UI and option params
            self.options[optName] += files
            widgetContent.set(';'.join(map(os.path.basename, self.options[optName])))
        return handler

    def validate_and_reset(submitFn):
        def manager(self):
            w = self.widgets
            self.options.update({
                'startTime': w['startTimeEnt']['self'].get(),
                'memList': w['memListEnt']['self'].get(),                
            })
            options = self.options

            # check start time format
            try:
                start_time = datetime.strptime(options['startTime'], '%Y-%m-%d %H:%M:%S')
                if start_time.hour >= 22:
                     start_time = start_time - timedelta(hours=4)  # because there is a magic error when time > 22pm.....
                options['startTime'] = start_time
            except ValueError:
                messagebox.showwarning('请检查','日期格式有误，请参考默认日期格式')
                w['startTimeEnt']['content'].set(datetime.now().strftime('%Y-%m-%d %H:%M:00')) # reset start time
                return

            # check files
            for file in [options['memList']] + list(options['beginSnapshot']) + list(options['endSnapshot']):
                if not os.path.exists(file):
                    messagebox.showwarning('请检查','文件不存在：' + file)
                    return

            submitFn(self, options)
            
            # reset
            self.reset_options()
            self.reset_ui()
        return manager

    @validate_and_reset
    def on_start_marking(self, options):
        """
        expect options:
        {
            'startTime': datetime object,
            'memList': validPath,
            'beginSnapshot': validPath,
            'endSnapshot': validPath,
            'savePath': defaultSavePath
        }
        """
        self.observers['do_roll_marking'](options)
    
    def on_start_cropping(self):
        pic_path = self.widgets['trainPicEnt']['self'].get()
        self.observers['do_cropping'](pic_path.split(' '))
        
    def on_start_training(self):
        lookup_path = self.widgets['lookupEnt']['self'].get()

        if not os.path.exists(lookup_path):
            messagebox.showwarning('请检查','无法找到查找表')
            return

        if not lookup_path.endswith('lookuptable01.csv'):
            messagebox.showwarning('请检查', '请将查找表放在assets文件夹内，并命名为lookuptable01.csv')
            return

        self.observers['do_training'](lookup_path)
    