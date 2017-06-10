from view import Application
from attendance_checker import Config, CheckerUtil, AttendanceChecker 
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
            util = CheckerUtil(config)
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
        'startTime': datetime(2017, 4, 2, 20, 30, 00),
        'classLength': [2, 0],
        'memList': '/Users/YuanZhong/Desktop/研讨班考勤软件/Recogniser/assets/考勤表.csv',
        'records': '/Users/YuanZhong/Desktop/研讨班考勤软件/AttendanceChecker/examples/2017_04_02.txt',
        'savePath': '/Users/YuanZhong/Desktop/研讨班考勤软件/AttendanceChecker/考勤结果/'
    }
    controller.onCheckAttendance(options)

if __name__ == '__main__':
#     test()
    mainView = tix.Tk()
    controller = Controller(mainView)
    controller.run()