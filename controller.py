from view import Application
from attendance_checker import UserParams, CheckerUtil, MemberSheet, AttendanceChecker
from attendance_checker import Database, Preprocessor, BWImage
from attendance_checker import read_json
from tkinter import tix
from datetime import datetime
from scipy.misc import imsave
import os, json, csv, itertools,  time

CURR_DIR = os.getcwd()

class Controller:
    def __init__(self, mainView=None):
        self.app = Application(callback=self.on_submit_options, master=mainView) if mainView else None
        self.member_sheet = None
        self.config = read_json('./config.json')
        self.db = Database(self.config).load()
        
        if self.app: self.app.log('==== 程序初始化 完毕 ====')

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
        if idx_unseen.any():
            self.save_unseen(screenshot.name, name_images[idx_unseen])

        if self.app:
            finish = time.time()
            self.app.log('完毕. 有{}张未识别图片已保存到未识别文件夹'.format(len(idx_unseen)))
            self.app.log('用时{}秒'.format('%0.3f' % (finish-start)))

        return names

    def on_submit_options(self, options):
        try:
            # prepare tools
            params = UserParams(options)
            util = CheckerUtil(params)
            if self.member_sheet is None:
                self.member_sheet = MemberSheet(options['memList'])
            
            # build the mockup record data -- prevent massive logic rewrite to attendance checker
            begin_names = list(itertools.chain.from_iterable(map(self.process_image, options['beginSnapshot'])))
            end_names  = list(itertools.chain.from_iterable(map(self.process_image, options['endSnapshot'])))
            record = util.synthesise_record(begin_names, end_names)

            # do attendance check
            checker = AttendanceChecker(params)
            checker.update_sheet(record)
            checker.conclude(self.member_sheet)

            # output results
            self.member_sheet.refresh()

            if self.app:
                self.app.log('------ 完成 ------')
                self.app.log('√ 考勤初表已更新')

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
        'memList': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\assets\\考勤初表.xlsx',
        'beginSnapshot': ('C:\\Users\\s400\\Desktop\\AttendanceChecker\\dev\\test3.png',),
        'endSnapshot': ('C:\\Users\\s400\\Desktop\\AttendanceChecker\\dev\\test1.png',),
        'savePath': 'C:\\Users\\s400\\Desktop\\AttendanceChecker\\考勤结果\\'
    }
    return controller.on_submit_options(options)

if __name__ == '__main__':
    # test()
    mainView = tix.Tk()
    controller = Controller(mainView)
    controller.run()
    