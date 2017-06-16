import pickle, sys, os, glob, json, csv
import numpy as np
from scipy.misc import imresize
from PIL import Image
from sklearn import svm
from sklearn import linear_model
from .util import selectEncoding

MIN_CONFIDENCE = -0.3

class Database:
	def __init__(self, config):
		self.config = config
		self.lookup_table = None
		self.classifier = None

	def __load_classifier(self, path):
		if os.path.exists(path):
			with open(path, 'rb') as model:
				self.classifier = pickle.load(model)
	
	@selectEncoding
	def __load_lookup(self, path, encoding=None):
		with open(path, 'r', encoding=encoding) as source:
			rawList = csv.DictReader(source)
			self.lookup_table = {
				int(row['number']): row['name']
				for row in rawList if row['number'] and row['name']
			}

	def lookup(self, images):
		"""
		predict the numeral class of each image array, then return the corresponding name for 
		certain ones and the index of uncertain ones in the original images list
		"""
		# get predicted numeral classes and corresponding confidence values
		predictions = []
		decision_vals = self.classifier.decision_function(images)
		for val in decision_vals:
			arg = np.argmax(val)
			predictions.append((arg, val[arg]))
		predictions = np.array(predictions)
		
		# separate certain and uncertain ones
		undecided = np.ravel(np.argwhere(predictions[:, 1] < MIN_CONFIDENCE))
		mask = np.ones(len(predictions), dtype=bool)
		mask[undecided] = False
		decided_kls = predictions[mask][:, 0]

		return [self.lookup_table[i] for i in decided_kls], undecided

	def study(self, images, labels, save_model=True, trainer=linear_model.LogisticRegression):
		# shaping
		if type(images) is not np.ndarray:
			images = np.array(images)
		if images.ndim > 2:
			images = images.reshape(len(images), -1)

		# training
		self.classifier = trainer().fit(images, labels)

		# saving
		if save_model:
			with open(self.config['classifier_path'], 'wb') as outfile:
				pickle.dump(self.classifier, outfile)

	def load(self):
		self.__load_lookup(self.config['lookup_path'])
		self.__load_classifier(self.config['classifier_path'])
		return self
