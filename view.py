import os, re
from datetime import datetime
from tkinter import Label, Entry, Button, StringVar
from tkinter.filedialog import askopenfilename
from tkinter import tix, messagebox

CURR_DIR = os.getcwd()
ASSET_DIR = os.path.join(CURR_DIR, 'assets')

class Application(tix.Frame):
    def __init__(self, callback, master=None):
        super().__init__(master)
        self.callback = callback
        self.wigets = {}

        self.pack()
        self.configWindow()
        self.createWidgets()
        self.positionWidgets()

    def configWindow(self):
        self.master.title('研讨班辅助考勤')
        self.master.maxsize(450, 300)
        self.master.minsize(450, 300)

    def buildStringVar(self, text):
        strVar = StringVar()
        strVar.set(text)
        return strVar

    def createWidgets(self):
        now = datetime.now()

        # setup start checking time
        startTimeVar = self.buildStringVar(now.strftime('%Y-%m-%d %H:%M:00'))
        startTimeLabel = Label(self, text='考勤开始时间')
        startTimeEnt = Entry(self, textvariable=startTimeVar)

        # setup class length
        clsLenVar = self.buildStringVar('2h 00min')
        clsLenLabel = Label(self, text='考勤长度')
        clsLenEnt = Entry(self, textvariable=clsLenVar)

        # member list file select
        defaultSheet = os.path.join(ASSET_DIR, '考勤表.csv')
        memListVar = self.buildStringVar(defaultSheet if os.path.exists(defaultSheet) else '')
        memListLabel = Label(self, text='学员列表')
        memListEnt = Entry(self, textvariable=memListVar)
        memListBtn = Button(self, text='选择文件', command=self.selectMemList)

        # attendance snapshots
        beginVar, endVar = self.buildStringVar(''), self.buildStringVar('')
        beginLabel, endLabel = Label(self, text='首次截图'), Label(self, text='结束截图')
        beginEnt, endEnt = Entry(self, textvariable=beginVar), Entry(self, textvariable=endVar)
        beginBtn = Button(self, text='选择文件', command=self.selectRecFile(True))
        endBtn = Button(self, text='选择文件', command=self.selectRecFile(False))

        # submit button
        submitBtn = Button(self,
            text="自动考勤",
            command=self.submitConfig)

        self.widgets = {
            'startTimeLabel': startTimeLabel,
            'startTimeEnt': { 'self': startTimeEnt, 'content': startTimeVar },
            'clsLenLabel': clsLenLabel,
            'clsLenEnt': {'self': clsLenEnt, 'content': clsLenVar },
            'memListLabel': memListLabel, 'memListBtn': memListBtn,
            'memListEnt': { 'self': memListEnt, 'content': memListVar},
            'beginLabel': beginLabel, 'beginBtn': beginBtn,
            'beginEnt': { 'self': beginEnt, 'content': beginVar},
            'endLabel': endLabel, 'endBtn': endBtn,
            'endEnt': { 'self': endEnt, 'content': endVar},
            'submitBtn': submitBtn
        }

    def positionWidgets(self):
        w = self.widgets # aliasing

        w['startTimeLabel'].grid(row=0, column=0, sticky='W', pady=10)
        w['startTimeEnt']['self'].grid(row=0, column=1, sticky='W', pady=10)

        w['clsLenLabel'].grid(row=1, column=0, sticky='W', pady=10)
        w['clsLenEnt']['self'].grid(row=1, column=1, sticky='W', pady=10)

        w['memListLabel'].grid(row=2, column=0, sticky='W', pady=10)
        w['memListEnt']['self'].grid(row=2, column=1, sticky='W', pady=10)
        w['memListBtn'].grid(row=2, column=2, sticky='W', pady=10, padx=10)

        w['beginLabel'].grid(row=3, column=0, sticky='W', pady=10)
        w['beginEnt']['self'].grid(row=3, column=1, sticky='W', pady=10)
        w['beginBtn'].grid(row=3, column=2, sticky='W', pady=10, padx=10)

        w['endLabel'].grid(row=4, column=0, sticky='W', pady=10)
        w['endEnt']['self'].grid(row=4, column=1, sticky='W', pady=10)
        w['endBtn'].grid(row=4, column=2, sticky='W', pady=10, padx=10)

        w['submitBtn'].grid(row=5, column=1, sticky='we')

    def selectMemList(self):
        filepath = askopenfilename(initialdir=CURR_DIR)
        self.widgets['memListEnt']['content'].set(filepath)

    def selectRecFile(self, isBegin=True):
        def handler():
            filepath = askopenfilename(initialdir=CURR_DIR)
            if isBegin:
                self.widgets['beginEnt']['content'].set(filepath)
            else:
                self.widgets['endEnt']['content'].set(filepath)
        return handler

    def validateOptions(submitFn):
        def validator(self):
            w = self.widgets
            options = {
                'startTime': w['startTimeEnt']['self'].get(),
                'classLength': w['clsLenEnt']['self'].get(),
                'memList': w['memListEnt']['self'].get(),
                'beginSnapshot': w['beginEnt']['self'].get(),
                'endSnapshot': w['endEnt']['self'].get(),
                'savePath': os.path.join(CURR_DIR, '考勤结果/')
            }

            # check start time format
            try:
                options['startTime'] = datetime.strptime(options['startTime'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                messagebox.showwarning('请检查','日期格式有误，请参考默认日期格式')
                w['startTimeEnt']['content'].set(datetime.now().strftime('%Y-%m-%d %H:%M:00')) # reset start time
                return

            # check class length format              
            regex = re.compile(r'^([0-9]+)h ([0-9]+)min$')
            res = regex.findall(options['classLength'])
            if not res:
                messagebox.showwarning('请检查','考勤长度格式有误，请参考默认格式')
                w['clsLenEnt']['content'].set('2h 30min') # reset class length
                return
            options['classLength'] = list(map(lambda val: int(val), res[0]))

            # check files
            for file in [options['memList'], options['beginSnapshot'], options['endSnapshot']]:
                if not os.path.exists(file):
                    messagebox.showwarning('请检查','文件不存在：' + file)
                    return

            submitFn(self, options)
        return validator


    @validateOptions
    def submitConfig(self, options):
        """
        expect options:
        {
            'startTime': datetime object,
            'classLength': [hours, minutes],
            'memList': validPath,
            'beginSnapshot': validPath,
            'endSnapshot': validPath,
            'savePath': defaultSavePath
        }
        """
        success, msg = self.callback(options)

        if not success:
            messagebox.showerror('请汇报技术人员', msg)
        else:
            messagebox.showinfo('考勤完毕', '考勤结果已保存至： ' + msg)

