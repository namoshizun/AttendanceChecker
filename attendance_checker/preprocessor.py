import sys, os, glob, json
import numpy as np
from sklearn.cluster import DBSCAN
from collections import Counter
from .db_manager import Database
from .image import BWImage
from .util import timing, first_occurrence


def read_config():
	with open('config.json', 'r+') as file:
		return json.load(file)


class Preprocessor:
	@staticmethod
	def clustering(img):
		clusters = DBSCAN(eps=0.1, min_samples=10).fit(img)
		return clusters.labels_

	@staticmethod
	def get_pivots(non_consecutive_arr):
		lows, highs = [0], [0]

		for idx, num in enumerate(non_consecutive_arr):
			highs[-1] = idx
			if num != non_consecutive_arr[lows[-1]]:
				lows.append(idx)
				highs.append(idx+1)

		return list(zip(lows, highs))

	@staticmethod
	def pad(img, size=(12, 180)):
		hpad = abs(img.shape[0] - size[0])
		wpad = abs(img.shape[1] - size[1])
		return np.pad(img, ((0, hpad), (0, wpad)), mode='edge')

	@staticmethod
	def crop_names(img, size=(12, 180)):
		me = Preprocessor
		h, w = size

		# get the most common start row position of a word
		labels = me.clustering(img)
		words = img[np.ravel(np.argwhere(labels == -1))]
		start_indexes_char = list(map(lambda w: first_occurrence(w, 0), words))
		common_start = Counter(start_indexes_char).most_common()[0][0]

		# get positions of continuous word blocks
		pivots = me.get_pivots(labels)
		words_pivots = list(filter(lambda _: all(labels[_[0]: _[1]] != 0), pivots))
		names = []

		# extract those word blocks, and 
		for p in words_pivots:
			name = img[p[0]: p[1]]
			croped = name[:h, common_start: common_start+w]
			names.append(croped if croped.shape == size else me.pad(croped, size))

		return names


@timing
def test():
	for name in wb_names:
		print(db.lookup(name))
	
"""
if __name__ == '__main__':
	# init database
	config = read_config()
	size = config['size']
	db = Database(config).load()

	# read screen shot and crop name segments
	screen_shot = BWImage('./dev/training.png')
	wb = screen_shot.wb
	wb_names = Preprocessor.crop_names(wb, size=(size['height'], size['width']))

	# lookup name segment tags
	# for name in wb_names:
	# 	print(db.lookup([np.ravel(name)]))

	# if you want to use names in this screen shot as database source
	# test_labels = list(range(len(wb_names)))
	# db.study(wb_names, test_labels, save_model=True)

"""