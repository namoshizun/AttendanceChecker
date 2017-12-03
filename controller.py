from view import Application
from attendance_checker import UserParams, CheckerUtil, MemberSheet, AttendanceChecker
from attendance_checker import Database, Preprocessor, BWImage
from attendance_checker import read_json
from tkinter import tix
from datetime import datetime
from scipy.misc import imsave
from itertools import chain
import os, json, csv, time, glob

CURR_DIR = os.getcwd()

class Controller:
    def __init__(self, mainView=None):
        self.app = Application(master=mainView) if mainView else None
        self.config = read_json('./config.json')
        self.db = Database(self.config).load()

        if self.app:
            self.app.on('do_roll_marking', self.do_roll_marking)
            self.app.on('do_cropping', self.do_cropping)
            self.app.on('do_training', self.do_training)

        self.do_logging('==== 程序初始化 完毕 ====')

    def save_unseen(self, folder, images):
        bucket = os.path.join('./待校验', folder)
        if not os.path.exists(bucket):
            os.makedirs(bucket)
        
        n_already_unseen = len(next(os.walk('./待校验'))[2])
        for i, img in enumerate(images):
            imsave(os.path.join(bucket, '{}.png'.format(n_already_unseen + i + 1)), img)
    
    def process_image(self, path, is_begin):
        """
        1. load the image at specified path
        2. crop out name segments
        3. query the database for the literal class of those name images.
        4. save unseen images
        """
        screenshot = BWImage(path)
        start = time.time()
        self.do_logging('> 处理图片.... {}'.format(screenshot.name))

        # get name segmeents
        h, w = self.config['size']['height'], self.config['size']['width']
        name_images = Preprocessor.crop_names(screenshot.wb, size=(h, w))

        # query datbase and save unseen ones
        names, idx_unseen = self.db.lookup(name_images.reshape(-1, h * w))
        if idx_unseen.any():
            self.save_unseen('进入' if is_begin else '退出', name_images[idx_unseen])

        finish = time.time()
        self.do_logging('完毕. 有{}张图片已保存到待校验文件夹'.format(len(idx_unseen)))
        self.do_logging('用时{}秒'.format('%0.3f' % (finish-start)))

        return names

    def do_logging(self, message):
        if self.app:
            self.app.log(message)

    def do_roll_marking(self, options):
        try:
            # prepare tools
            params = UserParams(options)
            util = CheckerUtil(params)
            member_sheet = MemberSheet(options['memList'])
            
            # build the mockup record data -- prevent massive logic rewrite to attendance checker
            begin_names = list(chain.from_iterable(map(lambda path: self.process_image(path, is_begin=True), options['beginSnapshot'])))
            end_names  = list(chain.from_iterable(map(lambda path: self.process_image(path, is_begin=False), options['endSnapshot'])))
            record = util.synthesise_record(begin_names, end_names)

            # do attendance check
            checker = AttendanceChecker(params)
            checker.update_sheet(record)
            not_marked = checker.conclude(member_sheet)

            # output results
            member_sheet.refresh()

            self.do_logging('------ 完成 ------')
            self.do_logging('√ 考勤初表已更新')
            self.do_logging('注： 以下名字未能在考勤初表找到对应条目: ')
            self.do_logging(os.linesep.join(not_marked))
            self.do_logging('------ 完成 ------')

        except Exception as e:
            self.do_logging('------ 发生错误 ------')
            self.do_logging('× 错误信息：{}'.format(str(e)))
    
    def do_cropping(self, pics):
        self.do_logging('==== 处理{}张训练图片 ===='.format(len(pics)))
        list(map(os.remove, glob.glob('./database/*.png')))  # clear old database folder

        counter = 0
        for pic in pics:
            screenshot = BWImage(pic)
            h, w = self.config['size']['height'], self.config['size']['width']
            name_crops = Preprocessor.crop_names(screenshot.wb, size=(h, w))
            for crop in name_crops:
                imsave('./database/{}.png'.format(counter), crop)
                counter += 1

        self.do_logging('database文件夹已更新')
        self.do_logging('------ 完成 ------')


    def do_training(self, lookup_path):
        train_pics = glob.glob('./database/*.png')

        self.do_logging('==== 训练{}张图片 ===='.format(len(train_pics)))
        X, Y = [], []
        for label, pic in enumerate(train_pics):
            X.append(BWImage(pic).wb)
            Y.append(label)
        
        self.db.study(X, Y)
        self.do_logging('------- 完成 -------')

    def run(self):
        self.app.mainloop()
    

if __name__ == '__main__':
    mainView = tix.Tk()
    controller = Controller(mainView)
    controller.run()
    