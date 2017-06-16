import os
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from scipy.misc import imresize, imsave
from PIL import Image
from .util import rgb2gray, gray2wb


class BWImage:
	def __init__(self, source_path):
		img = mpimg.imread(source_path)

		self.wb = gray2wb(rgb2gray(img) if img.ndim > 2 else img)
		self.source = source_path
		self.name = self.__img_name__(source_path)

	def __img_name__(self, fpath):
		base = os.path.basename(fpath)
		return os.path.splitext(base)[0]

	def show(self):
		plt.imshow(self.wb, cmap = plt.get_cmap('gray'))
		plt.show()

	def resize(self, size):
		self.wb = imresize(self.wb, size)
	
	def save(self,filename):
		imsave(filename, self.wb)
