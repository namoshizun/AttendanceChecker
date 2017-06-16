from view import Application
from attendance_checker import UserParams, CheckerUtil, AttendanceChecker 
from attendance_checker import Database, Preprocessor, BWImage
from attendance_checker import selectEncoding, readJSON, timing
from tkinter import tix
from datetime import datetime
from scipy.misc import imsave
import numpy as np
import os, json, csv

CURR_DIR = os.getcwd()

class Controller:
    def __init__(self, mainView=None):
        if mainView:
            self.app = Application(callback=self.onCheckAttendance, master=mainView)
        self.member_sheet = None
        self.config = readJSON('./config.json')
        self.db = Database(self.config).load()
    
    @selectEncoding
    def read_member_sheet(self, path, encoding=None):
        with open(path, 'r', encoding=encoding) as source:
            rawList = csv.DictReader(source)

            return {row['YY昵称'].strip() for row in rawList if row['YY昵称']}

    def save_unseen(self, folder, images):
        bucket = os.path.join('./未识别', folder)
        if not os.path.exists(bucket):
            os.makedirs(bucket)
        
        for i, img in enumerate(images):
            imsave(os.path.join(bucket, '{}.png'.format(i)), img)
    
    @timing
    def process_image(self, screenshot):
        """
        1. load the image at specified path
        2. crop out name segments
        3. query the database for the literal class of those name images.
        4. save unseen images
        """
        # get name segmeents
        h, w = self.config['size']['height'], self.config['size']['width']
        name_images = Preprocessor.crop_names(screenshot.wb, size=(h, w))

        # query datbase and save unseen ones
        names, idx_unseen = self.db.lookup(name_images.reshape(-1, h * w))
        self.save_unseen(screenshot.name, name_images[idx_unseen])

        return names

    def onCheckAttendance(self, options):
        try:
            # prepare tools
            unrecognised = set()
            params = UserParams(options)
            util = CheckerUtil(params)
            if self.member_sheet is None:
                self.member_sheet = self.read_member_sheet(options['memList'])
            
            # build the mockup record data -- prevent massive logic rewrite to attendance checker
            beginNames = self.process_image(BWImage(options['beginSnapshot']))
            endNames = self.process_image(BWImage(options['endSnapshot']))
            record = util.synthesise_record(beginNames, endNames)

            # do attendance check
            checker = AttendanceChecker(self.member_sheet, params)
            checker.updateSheet(records)
            checker.conclude()

            # # output results
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
        'memList': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\assets\\考勤表.csv',
        'beginSnapshot': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\dev\\training.png',
        'endSnapshot': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\dev\\training.png',
        'savePath': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\考勤结果\\'
    }
    controller.onCheckAttendance(options)

if __name__ == '__main__':
    test()
    # mainView = tix.Tk()
    # controller = Controller(mainView)
    # controller.run()