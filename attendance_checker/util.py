import time, sys, json
import numpy as np
import matplotlib.pyplot as plt


#############
# MISC UTIL #
#############
def readJSON(path):
    with open('config.json', 'r') as file:
        return json.load(file)


######################
# TEXT PREPROCESSING #
######################
DEFAULT_ENC = sys.getdefaultencoding()
def selectEncoding(ioFn):
    encodings = ['utf-8', 'utf-16', 'gb18030', 'gb2312', 'gbk']

    def detectEncoding(path, idx=0):
        try:
            with open(path, encoding=encodings[idx]) as source:
                source.read()
            return True, encodings[idx]
        except IndexError:
            return False, None
        except UnicodeDecodeError:
            return detectEncoding(path, idx+1)


    def checker(self, path):
        succ, encoding = detectEncoding(path)
        if succ:
            return ioFn(self, path, encoding)
        else:
            raise UnicodeDecodeError('cannot decode file ' + path)
    return checker

#######################
# IMAGE PREPROCESSING #
#######################
def rgb2gray(rgb):
	return np.dot(rgb[...,:3], [0.3, 0.59, 0.11])


def gray2wb(gray, normalise=True):
	bools = gray != 0.0
	gray[bools] = 255 if not normalise else 1.0
	return gray


def timing(f):
    def timmer(*args, **kwargs):
        start = time.time()
        ret = f(*args, **kwargs)
        finish = time.time()
        print('%s function took %0.3f s' % (f.__name__, (finish-start)))
        return ret
    return timmer


def draw(*args):
    for i, img in enumerate(args):
        plt.subplot(2, 1, i + 1)
        plt.imshow(img)
    plt.show()


def first_occurrence(arr, val):
    for i, v in enumerate(arr):
        if v == val:
            return i

    return -1
