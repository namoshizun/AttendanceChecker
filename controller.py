from view import Application
from attendance_checker import UserParams, CheckerUtil, AttendanceChecker 
from attendance_checker import Database, Preprocessor, BWImage
from tkinter import tix
from datetime import datetime
import numpy as np
import os, json


CURR_DIR = os.getcwd()

class Controller:
    def __init__(self, mainView=None):
        if mainView:
            self.app = Application(callback=self.onCheckAttendance, master=mainView)
        self.memberList = None
        self.config = self.readConfig()
        self.db = Database(self.config)
    
    def readConfig(self):
        with open('config.json', 'r+') as file:
            return json.load(file)
    
    def readSnapshot(self, path):
        h, w = self.config['size']['height'], self.config['size']['width']
        screenshot = BWImage(path)
        wb_names = Preprocessor.crop_names(screenshot.wb, size=(h, w))
        return [self.db.lookup([np.ravel(name)]) for name in wb_names]

    def onCheckAttendance(self, options):
        try:
            # prepare tools
            params = UserParams(options)
            util = CheckerUtil(params)
            if self.memberList is None:
                self.memberList = util.readMemberList(options['memList'])
            
            # build the mockup record data -- prevent massive logic rewrite to attendance checker
            beginNames = self.readSnapshot(options['beginSnapshot'])
            endNames = self.readSnapshot(options['endSnapshot'])
            record = util.synthesise_record(beginNames, endNames)

            # do attendance check
            checker = AttendanceChecker(self.memberList, params)
            checker.updateSheet(record)
            checker.conclude()

            # output results
            saveTo = util.outputAttendence(params.savePath, checker.sheet)
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