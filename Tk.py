import os, re
from datetime import datetime
from tkinter import Label, Entry, Button, StringVar
from tkinter import tix, messagebox
from tkinter.filedialog import askopenfilename

CURR_DIR = os.getcwd()

class Application(tix.Frame):
    def __init__(self, callback, master=None):
        super().__init__(master)
        self.callback = callback
        self.wigets = {}

        self.pack()
        self.configWindow()
        self.createWidgets()
        self.locateWidgets()

    def configWindow(self):
        self.master.title('研讨班辅助考勤')
        self.master.maxsize(450, 250)
        self.master.minsize(450, 250)

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
        tmp = os.path.join(CURR_DIR, '考勤表.csv')
        memListVar = self.buildStringVar(tmp if os.path.exists(tmp) else '')
        memListLabel = Label(self, text='学员列表')
        memListEnt = Entry(self, textvariable=memListVar)
        memListBtn = Button(self, text='选择文件', command=self.selectMemList)

        # record file select
        recVar = self.buildStringVar('')
        recLabel = Label(self, text='进出记录')
        recEnt = Entry(self, textvariable=recVar)
        recBtn = Button(self, text='选择文件', command=self.selectRecFile)

        # submit button
        submitBtn = Button(self,
            text="自动考勤",
            command=self.submitConfig)

        self.widgets = {
            'startTimeLabel': startTimeLabel,
            'clsLenLabel': clsLenLabel,
            'memListLabel': memListLabel, 'memListBtn': memListBtn,
            'recLabel': recLabel, 'recBtn': recBtn,
            'startTimeEnt': { 'self': startTimeEnt, 'content': startTimeVar },
            'memListEnt': { 'self': memListEnt, 'content': memListVar},
            'recEnt': { 'self': recEnt, 'content': recVar},
            'clsLenEnt': {'self': clsLenEnt, 'content': clsLenVar },
            'submitBtn': submitBtn
        }

    def locateWidgets(self):
        w = self.widgets # aliasing

        w['startTimeLabel'].grid(row=0, column=0, sticky='W', pady=10)
        w['startTimeEnt']['self'].grid(row=0, column=1, sticky='W', pady=10)

        w['clsLenLabel'].grid(row=1, column=0, sticky='W', pady=10)
        w['clsLenEnt']['self'].grid(row=1, column=1, sticky='W', pady=10)

        w['memListLabel'].grid(row=2, column=0, sticky='W', pady=10)
        w['memListEnt']['self'].grid(row=2, column=1, sticky='W', pady=10)
        w['memListBtn'].grid(row=2, column=2, sticky='W', pady=10, padx=10)

        w['recLabel'].grid(row=3, column=0, sticky='W', pady=10)
        w['recEnt']['self'].grid(row=3, column=1, sticky='W', pady=10)
        w['recBtn'].grid(row=3, column=2, sticky='W', pady=10, padx=10)

        w['submitBtn'].grid(row=4, column=1, sticky='we')

    def selectMemList(self):
        filepath = askopenfilename(initialdir=CURR_DIR)
        self.widgets['memListEnt']['content'].set(filepath)

    def selectRecFile(self):
        filepath = askopenfilename(initialdir=CURR_DIR)
        self.widgets['recEnt']['content'].set(filepath)

    def validateInputs(submitFn):
        def validator(self):
            w = self.widgets
            options = {
                'startTime': w['startTimeEnt']['self'].get(),
                'classLength': w['clsLenEnt']['self'].get(),
                'memList': w['memListEnt']['self'].get(),
                'records': w['recEnt']['self'].get(),
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
            for file in [options['memList'], options['records']]:
                if not os.path.exists(file):
                    messagebox.showwarning('请检查','文件不存在：' + file)
                    return

            submitFn(self, options)
        return validator


    @validateInputs
    def submitConfig(self, options):
        """
        expect options:
        {
            'startTime': datetime object,
            'classLength': [hours, minutes],
            'memList': validPath,
            'records': validPath,
            'savePath': defaultSavePath
        }
        """
        success, msg = self.callback(options)

        if not success:
            messagebox.showerror('请汇报技术人员', msg)
        else:
            messagebox.showinfo('考勤完毕', '考勤结果已保存至： ' + msg)

