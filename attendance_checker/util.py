import time
import numpy as np
import matplotlib.pyplot as plt


def rgb2gray(rgb):
	return np.dot(rgb[...,:3], [0.3, 0.59, 0.11])


def gray2wb(gray):
	bools = gray != 0.0
	gray[bools] = 255
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
