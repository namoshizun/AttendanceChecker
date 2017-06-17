from view import Application
from attendance_checker import UserParams, CheckerUtil, AttendanceChecker 
from attendance_checker import Database, Preprocessor, BWImage
from attendance_checker import selectEncoding, readJSON
from tkinter import tix
from datetime import datetime
from scipy.misc import imsave
import numpy as np
import os, json, csv, itertools,  time

CURR_DIR = os.getcwd()

class Controller:
    def __init__(self, mainView=None):
        self.app = Application(callback=self.onCheckAttendance, master=mainView) if mainView else None
        self.member_sheet = None
        self.config = readJSON('./config.json')
        self.db = Database(self.config).load()
        
        if self.app: self.app.log('==== 程序初始化 完毕 ====')

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
    
    def process_image(self, path):
        """
        1. load the image at specified path
        2. crop out name segments
        3. query the database for the literal class of those name images.
        4. save unseen images
        """
        screenshot = BWImage(path)
        if self.app:
            start = time.time()
            self.app.log('> 处理图片.... {}'.format(screenshot.name))

        # get name segmeents
        h, w = self.config['size']['height'], self.config['size']['width']
        name_images = Preprocessor.crop_names(screenshot.wb, size=(h, w))

        # query datbase and save unseen ones
        names, idx_unseen = self.db.lookup(name_images.reshape(-1, h * w))
        self.save_unseen(screenshot.name, name_images[idx_unseen])

        if self.app:
            finish = time.time()
            self.app.log('完毕. 有{}张未识别图片已保存到未识别文件夹'.format(len(idx_unseen)))
            self.app.log('用时{}秒'.format('%0.3f' % (finish-start)))

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
            beginNames = list(itertools.chain.from_iterable(map(self.process_image, options['beginSnapshot'])))
            endNames = list(itertools.chain.from_iterable(map(self.process_image, options['endSnapshot'])))
            record = util.synthesise_record(beginNames, endNames)

            # do attendance check
            checker = AttendanceChecker(self.member_sheet, params)
            checker.updateSheet(record)
            checker.conclude()

            # # output results
            saveTo = util.outputAttendence(params.savePath, checker.sheet)

            if self.app:
                self.app.log('------ 完成 ------')
                self.app.log('√ 考勤结果已保存到: {}'.format(os.path.join(CURR_DIR, '考勤结果/' + saveTo)))

        except Exception as e:
            if self.app:
                self.app.log('------ 发生错误 ------')
                self.app.log('× 错误信息：{}'.format(str(e)))

    def run(self):
        self.app.mainloop()

def test():
    controller = Controller()
    options = {
        'startTime': datetime(2017, 4, 2, 20, 30, 00),
        'classLength': [2, 0],
        'memList': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\assets\\考勤表.csv',
        'beginSnapshot': ('C:\\Users\\s400\\Desktop\\AttendanceChecker\\dev\\training.png',),
        'endSnapshot': ('C:\\Users\\s400\\Desktop\\AttendanceChecker\\dev\\test1.png',),
        'savePath': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\考勤结果\\'
    }
    return controller.onCheckAttendance(options)

if __name__ == '__main__':
    # test()
    mainView = tix.Tk()
    controller = Controller(mainView)
    controller.run()
    