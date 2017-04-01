# -*- coding: UTF-8 -*-
from Tk import Application
from AttendanceChecker import Config, Util, AttendanceChecker
from tkinter import tix
from datetime import datetime
import os

CURR_DIR = os.getcwd()

class Controller:
    def __init__(self, mainView=None):
        if mainView:
            self.app = Application(callback=self.onCheckAttendance, master=mainView)
        self.memberList = None

    def onCheckAttendance(self, options):
        try:
            config = Config(options)
            util = Util(config)
            if self.memberList is None:
                self.memberList = util.readMemberList(options['memList'])

            record = util.readNewRecord(config.records)
            checker = AttendanceChecker(self.memberList, config)
            checker.updateSheet(record)

            checker.conclude()
            saveTo = util.outputAttendence(config.savePath, checker.sheet)
            return True, os.path.join(CURR_DIR, '考勤结果/' + saveTo)

        except Exception as e:
            print(e)
            return False, str(e)

    def run(self):
        self.app.mainloop()

def test():
    controller = Controller()
    options = {
        'startTime': datetime(2017, 3, 26, 8, 30, 00),
        'classLength': [2, 0],
        'memList': 'C:\\Users\\s400\\Desktop\\研讨班软件\\AttendanceChecker\\AttendanceChecker\\考勤表.csv',
        'records': 'C:\\Users\\s400\\Desktop\\研讨班软件\\AttendanceChecker\\AttendanceChecker\\examples\\20170326.txt',
        'savePath': 'C:\\Users\\s400\\Desktop\\研讨班软件\\AttendanceChecker\\AttendanceChecker\\考勤结果\\'
    }
    controller.onCheckAttendance(options)

if __name__ == '__main__':
    # test()
    mainView = tix.Tk()
    controller = Controller(mainView)
    controller.run()