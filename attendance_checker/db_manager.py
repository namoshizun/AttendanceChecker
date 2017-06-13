import pickle
import sys, os, glob, json
import numpy as np
from scipy.misc import imresize
from PIL import Image
from sklearn import svm
from sklearn import linear_model
from .image import BWImage

class Database:
	def __init__(self, config):
		self.config = config
		self.db_path = config['db_path']
		self.classifier_path = config['classifier_path']
		self.classifier = None

	def lookup(self, img):
		return self.classifier.predict(img)[0]

	def study(self, images, labels, save_model=True):
		# shaping
		if type(images) is not np.ndarray:
			images = np.array(images)
		if images.ndim > 2:
			images = images.reshape(len(images), -1)

		# training
		# self.classifier = svm.SVC(gamma=0.001).fit(images, labels)
		# self.classifier = linear_model.LinearRegression().fit(images, labels)
		self.classifier = linear_model.LogisticRegression().fit(images, labels)

		# saving
		if save_model:
			with open(self.classifier_path, 'wb') as outfile:
				pickle.dump(self.classifier, outfile)

	def load(self):
		if os.path.exists(self.classifier_path):
			with open(self.classifier_path, 'rb') as model:
				self.classifier = pickle.load(model)

		return self

	def renew(self, raw, names=None):
		size = (self.config['size']['height'], self.config['size']['width'])
		if type(raw) is not list:
			raw = [raw]

		for i, img in enumerate(raw):
			if img.shape != size:
				img = imresize(img, size)

			im = Image.fromarray(img).convert('RGB')
			name = '{}.png'.format(names[i] if names else i)
			im.save(os.path.join(self.db_path, name))

