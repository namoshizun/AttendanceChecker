import os, re, itertools
from datetime import datetime, timedelta
from tkinter import Label, Entry, Button, StringVar, Text, Scrollbar
from tkinter.filedialog import askopenfilenames
from tkinter import tix, messagebox

CURR_DIR = os.getcwd()
ASSET_DIR = os.path.join(CURR_DIR, 'assets')

class Application(tix.Frame):
    def __init__(self, callback, master=None):
        super().__init__(master)
        self.callback = callback
        self.options = {}
        self.wigets = {}

        self.reset_options()
        self.pack()
        self.config_window()
        self.create_widgets()
        self.position_widgets()

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
        self.master.maxsize(650, 300)
        self.master.minsize(650, 300)

    def build_string_var(self, text):
        strVar = StringVar()
        strVar.set(text)
        return strVar

    def create_widgets(self):
        now = datetime.now()

        # setup start checking time
        startTimeVar = self.build_string_var(now.strftime('%Y-%m-%d %H:%M:00'))
        startTimeLabel = Label(self, text='考勤开始时间')
        startTimeEnt = Entry(self, textvariable=startTimeVar, width=30)

        # member list file select
        defaultSheet = os.path.join(ASSET_DIR, '考勤初表.xlsx')
        memListVar = self.build_string_var(defaultSheet if os.path.exists(defaultSheet) else '')
        memListLabel = Label(self, text='学员列表')
        memListEnt = Entry(self, textvariable=memListVar, width=30)
        memListBtn = Button(self, text='选择文件', command=self.select_mem_list)

        # attendance snapshots
        beginVar, endVar = self.build_string_var(''), self.build_string_var('')
        beginLabel, endLabel = Label(self, text='首次截图'), Label(self, text='结束截图')
        beginEnt, endEnt = Entry(self, textvariable=beginVar, width=30), Entry(self, textvariable=endVar, width=30)
        beginBtn = Button(self, text='添加文件', command=self.select_screenshots(is_begin=True))
        endBtn = Button(self, text='添加文件', command=self.select_screenshots(is_begin=False))

        # submit button
        submitBtn = Button(self,
            text="自动考勤",
            command=self.submitConfig)

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
            'logPanel': Text(self)
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
        w['logPanel'].grid(row=0, column=3, columnspan=2, rowspan=5, sticky='nsew')

    def select_mem_list(self):
        filepath = askopenfilenames(initialdir=CURR_DIR)
        self.widgets['memListEnt']['content'].set(filepath)

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
    def submitConfig(self, options):
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
        self.callback(options)
