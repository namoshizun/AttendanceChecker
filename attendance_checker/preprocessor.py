import numpy as np
from sklearn.cluster import DBSCAN
from collections import Counter
from .db_manager import Database
from .image import BWImage
from .util import first_occurrence


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
	def pad(img, size):
		hpad = abs(img.shape[0] - size[0])
		wpad = abs(img.shape[1] - size[1])
		return np.pad(img, ((0, hpad), (0, wpad)), mode='edge')

	@staticmethod
	def crop_names(img, size):
		me = Preprocessor
		h, w = size

		# get row labels (0 = white, -1 = black)
		labels = me.clustering(img)

		# get positions of continuous word blocks
		pivots = me.get_pivots(labels)
		words_pivots = list(filter(lambda _: all(labels[_[0]: _[1]] != 0), pivots))

		# extract those word blocks
		name_imgs = []
		for p in words_pivots:
			snippet = img[p[0]: p[1]]
			start_indexes_char = list(map(lambda w: first_occurrence(w, 0), snippet))
			common_start = Counter(start_indexes_char).most_common()[0][0]

			# add empty paddings if the cropped image is smaller than the standard size
			croped = snippet[:h, common_start: common_start+w]
			name_imgs.append(croped if croped.shape == size else me.pad(croped, size))

		return np.array(name_imgs)
