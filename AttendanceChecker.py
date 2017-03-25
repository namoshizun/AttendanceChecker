# -*- coding: UTF-8 -*-
import re, json
import os, csv
from datetime import datetime, timedelta
from itertools import chain, zip_longest

class Config:
	def __attach__(self, newProps):
		for key, value in newProps.items():
			self.__dict__[key] = value
		return self

	def configFile(self, props):
		for key, file in props.items():
			if key != 'savePath' and not os.path.exists(file):
				raise FileNotFoundError(key + ' does not exist')
		self.__attach__(props)
		return self

	def classLength(self, props):
		assert(type(props['period']) is int)
		assert(props['unit'] in ['minutes', 'hours'])
		self.__attach__(props)
		return self

	def timestamp(self, props):
		for key, ts in props.items():
			assert(type(ts) is datetime)
		self.__attach__(props)
		return self

class Util:
	def __init__(self, config):
		self.config = config
		self.parser = RecordsParser()

	def readMemberList(self, path):
		with open(path, 'r+', encoding='UTF-8') as source:
			rawList = csv.DictReader(source)
			return [row['考勤系统YY昵称'] for row in rawList]

	def readNewRecord(self, path):
		with open(path, 'r+', encoding='UTF-8') as source:
			rawLines = source.read().splitlines()
			return self.parser.rawToDicts(rawLines)

	def outputAttendence(self, path, sheet):
		if not os.path.exists(path):
			os.makedirs(path)
		summ = sheet.summary
		fname = str(self.config.start.date()) + '.csv'

		with open(os.path.join(path, fname), 'w+', newline='', encoding='UTF-8') as outfile:
			cout = csv.writer(outfile, delimiter=',')
			cout.writerow(['考勤时间', '-'.join(list(map(lambda dte: str(dte), summ['period'])))])
			cout.writerow(['出勤', summ['fullAttendances']])
			cout.writerow(['早退', summ['earlyLeaves']])
			cout.writerow(['迟到', summ['lates']])
			cout.writerow(['中途长期退出', summ['dropouts']])
			cout.writerow(['YY昵称','出勤结果', '活动记录'])

			cout.writerows(self.parser.parseSheetToCsvRows(sheet))
			cout.writerow(['未识别', ' | '.join(list(sheet.summary['unrecognised']))])


class RecordsParser:
	def __init__(self):
		self.regex = re.compile(r"[^[]*\[([^]]*)\] (进入|退出) [^[]*\[([^]]*)\] 频道。\((.*?)\)")

	def rawToDicts(self, source):
		ret = []
		for line in source:
			match = self.regex.findall(line)
			if len(match) == 1:
				_ = match[0]
				ret.append({
					'name': _[0],
					'action': _[1],
					'time': _[3]
				})
		return ret

	def parseSheetToCsvRows(self, sheet):
		rows = []
		def translateAttendance(dropout=False, earlyLeave=False, late=False):
			ret = ''
			if dropout: ret += '中途长期退出'
			if earlyLeave: ret += '早退'
			if late: ret += '迟到'
			return ret + '全勤' if ret == '' else ret

		for name, hist in sheet.mems.items():
			fullRec = []
			for i, dte in enumerate(chain.from_iterable(zip_longest(hist['enter'], hist['leave']))):
				if dte:
					fullRec.append(('进' if i%2==0 else '退')+str(dte))

			rows.append([
				# YY昵称
				name,
				# 出勤结果
				translateAttendance(**hist['attendance']),
				# 进出记录 -- 方便起见先这样写了,比较难看 o.o
				' '.join(fullRec)
			])
		return rows


class AttendancSheet:
	def __init__(self, config):
		def calcEnd():
			return config.start + {
				'hours': timedelta(hours=config.period),
				'minutes': timedelta(minutes=config.period)
			}.get(config.unit)

		self.summary = {
			'fullAttendances': None,
			'earlyLeaves': None,
			'dropouts': None,
			'lates': None,
			'unrecognised': set(),
			'period': [config.start, calcEnd()],
		}
		self.mems = {}

	def signin(self, name):
		self.mems[name] = {
			'enter': [],
			'leave': [],
			'attendance': {'late': False, 'dropout': False, 'earlyLeave': False}
		}

	def memEnter(self, name, time):
		self.mems[name]['enter'] += [time]
		if self.mems[name]['leave']:
			# mark as 'dropout' if unpresent time is longer than 15mins
			if (self.mems[name]['leave'][-1] - time).seconds > 15*60:
				self.mems[name]['attendance']['dropout'] = True

	def memLeave(self, name, time):
		self.mems[name]['leave'] += [time]

	def conclude(self):
		fullAttendances, earlyLeaves, lates, total = 0, 0, 0, len(self.mems)

		for mem, hist in self.mems.items():
			if (hist['enter'][0] - self.summary['period'][0]).seconds > 15*60:
				self.mems[mem]['attendance']['late'] = True
				lates += 1

			if hist['leave'] and (self.summary['period'][1] - hist['leave'][-1]).seconds > 15*60:
				self.mems[mem]['attendance']['earlyLeave'] = True
				earlyLeaves += 1				

		fullAttendances = sum(1 if not hist['attendance']['dropout'] and \
			not hist['attendance']['earlyLeave'] and \
			not hist['attendance']['late'] else 0 for _, hist in self.mems.items())
		dropouts = sum(1 if hist['attendance']['dropout'] else 0 for _, hist in self.mems.items())

		self.summary['fullAttendances'] = '{}/{}'.format(fullAttendances, total)
		self.summary['dropouts'] = '{}/{}'.format(dropouts, total)
		self.summary['earlyLeaves'] = '{}/{}'.format(earlyLeaves, total)
		self.summary['lates'] = '{}/{}'.format(lates, total)


class AttendanceChecker:
	def __init__(self, memberList, config):
		self.config = config
		self.sheet = AttendancSheet(config)

		self.memberList = memberList
		self.lastCheck = config.start

	def updateSheet(self, newRec):
		toDtm = lambda _str: datetime.strptime(str(config.start.date()) + '-' + _str, '%Y-%m-%d-%H:%M:%S')

		for rec in newRec:
			dtime, action, name = toDtm(rec['time']), rec['action'], rec['name']

			if dtime <= self.lastCheck:
				# skip old records
				continue

			if name not in self.memberList:
				# take note of unrecognised name
				self.sheet.summary['unrecognised'].add(name)
				continue

			if name not in self.sheet.mems:
				# create new entry for members not yet in the attendance sheet
				self.sheet.signin(name)

			# mark every enter and leave, and do the attendance check.
			if action == '进入':
				self.sheet.memEnter(name, dtime)
			elif action == '退出':
				self.sheet.memLeave(name, dtime)

		self.lastCheck = toDtm(newRec[-1]['time'])


	def conclude(self):
		self.sheet.conclude()


def main(config):
	# READ
	util = Util(config)
	memberList = util.readMemberList(config.memListPath)
	_1stRecord = util.readNewRecord(config._1stRecPath)
	_2ndecord = util.readNewRecord(config._2ndRecPath)
	_3rdRecord = util.readNewRecord(config._3rdRecPath)

	# COMPUTE
	checker = AttendanceChecker(memberList, config)
	checker.updateSheet(_1stRecord)
	checker.updateSheet(_2ndecord)
	checker.updateSheet(_3rdRecord)

	# SAVE
	checker.conclude()
	util.outputAttendence(config.savePath, checker.sheet)

	print('\n====\ndone')

if __name__ == '__main__':
	config = Config()\
		.configFile({
			'memListPath': './examples/研讨班名单.csv',
			'_1stRecPath': './examples/2017-03-20-00-26-00.txt',
			'_2ndRecPath': './examples/2017-03-20-00-27-00.txt',
			'_3rdRecPath': './examples/2017-03-20-00-29-00.txt',
			'savePath': './考勤结果/'
		})\
		.classLength({
			'period': 3,
			'unit': 'minutes'
		})\
		.timestamp({
			'start': datetime(2017, 3, 20, 00, 25, 00)
		})

	main(config)