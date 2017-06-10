import re, json, sys
import os, csv, codecs
from datetime import datetime, timedelta
from itertools import chain, zip_longest
from functools import reduce

DEFAULT_ENC = sys.getdefaultencoding()
MAX_TIME = datetime.now() + timedelta(9999)

class Config:
	def __init__(self, options):
		self.__attach__(options)

	def __attach__(self, newProps):
		for key, value in newProps.items():
			self.__dict__[key] = value
		return self

class CheckerUtil:
	def __init__(self, config):
		self.config = config
		self.parser = RecordsParser()

	def checkEncoding(ioFn):
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

	@checkEncoding
	def readMemberList(self, path, encoding=DEFAULT_ENC):
		with open(path, 'r+', encoding=encoding) as source:
			rawList = csv.DictReader(source)
			return [row['YY昵称'] for row in rawList if row['YY昵称']]

	@checkEncoding
	def readNewRecord(self, path, encoding=DEFAULT_ENC):
		with open(path, 'r+', encoding=encoding) as source:
			rawLines = source.read().splitlines()
			return self.parser.rawToDicts(rawLines)

	def outputAttendence(self, path, sheet):
		if not os.path.exists(path):
			os.makedirs(path)
		summ = sheet.summary
		fname = str(self.config.startTime.date()) + '.csv'

		with open(os.path.join(path, fname), 'w+', newline='', encoding='utf-8-sig') as outfile:
			cout = csv.writer(outfile, delimiter=',')
			cout.writerow(['考勤时间', '-'.join(list(map(lambda dte: str(dte), summ['period'])))])
			cout.writerow(['全勤', summ['stat']['present']])
			cout.writerow(['早退', summ['stat']['earlyLeaves']])
			cout.writerow(['迟到', summ['stat']['lates']])
			cout.writerow(['缺勤', summ['stat']['absent']])
			cout.writerow(['中途长期退出', summ['stat']['dropouts']])
			cout.writerow(['未识别名单'] + list(summ['unrecognised']))
			cout.writerow(['YY昵称','出勤结果', '活动记录'])
			cout.writerows(self.parser.parseSheetToCsvRows(sheet))
		return fname


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
		def translateAttendance(dropout=False, earlyLeave=False, late=False, absent=False):
			ret = ''
			if dropout: ret += '中途长期退出+'
			if earlyLeave: ret += '早退+'
			if late: ret += '迟到+'
			if absent: ret += '缺勤+'
			return ret + '全勤+' if ret == '' else ret

		for name, hist in sheet.mems.items():
			fullRec = [('进' if i%2==0 else '退')+str(dte) for i, dte in enumerate(chain.from_iterable(zip_longest(hist['enter'], hist['leave']))) if dte]

			rows.append([
				# YY昵称
				name,
				# 出勤结果
				translateAttendance(**hist['attendance']),
				# 进出记录
				' '.join(fullRec)
			])
		# add absent folks separately
		list(map(lambda absentName: rows.append([absentName, '缺勤+']), sheet.summary['absent']))
		# sort by attendance result
		rows.sort(key=lambda x: x[1])

		return rows


class AttendancSheet:
	def __init__(self, config):
		endTime = config.startTime + timedelta(minutes=config.classLength[0]*60+config.classLength[1])
		self.summary = {
			'stat': {
				'present': None,
				'earlyLeaves': None,
				'dropouts': None,
				'lates': None,
				'absent': None,
			},
			'absent': None,
			'unrecognised': set(),
			'period': [config.startTime, endTime],
		}
		self.mems = {}

	def signin(self, name):
		self.mems[name] = {
			'enter': [],
			'leave': [],
			'attendance': {'late': False, 'dropout': False, 'earlyLeave': False, 'absent': False}
		}

	def memEnter(self, name, time):
		if time in self.mems[name]['enter']:
			return
		self.mems[name]['enter'].append(time)
		self.mems[name]['leave'].append(MAX_TIME) # placeholder

	def memLeave(self, name, time):
		if time in self.mems[name]['leave']:
			return
		self.mems[name]['leave'][-1] = time # polyfill

	def conclude(self, memberList):

		present, earlyLeaves, dropouts, lates, total = 0, 0, 0, 0, len(memberList)
		start, end = self.summary['period'][0], self.summary['period'][1]
		absence = list(set(memberList) - set(self.mems.keys()))

		for mem, hist in self.mems.items():
			pairs = list(zip(hist['enter'], hist['leave']))
			pairs = list(filter(lambda p: p[1] >= start and p[0] <= end, pairs)) # trim unimportant pairs

			# fail to present a valid attendance
			if not pairs:
				self.mems[mem]['attendance']['absent'] = True
				absence.append(mem)

			else:
				# first enter - start > treshold
				if pairs[0][0] > start and (pairs[0][0] - start).seconds > 15*60:
					self.mems[mem]['attendance']['late'] = True
					lates += 1

				# end - last leave > treshold
				if end > pairs[-1][1] and (end - pairs[-1][1]).seconds > 15*60:
					self.mems[mem]['attendance']['earlyLeave'] = True
					earlyLeaves += 1

				# basicially traverse pairs interleavely and check if there is any time gap longer than 15mins
				dropoutDet = reduce(lambda acc, curr: [curr[1], (curr[0]-acc[0]).seconds > 15*60], pairs, [pairs[0][0], False])
				if dropoutDet[1]:
					self.mems[mem]['attendance']['dropout'] = True
					dropouts += 1


		present = sum(1 if not hist['attendance']['dropout'] and \
			not hist['attendance']['earlyLeave'] and \
			not hist['attendance']['absent'] and \
			not hist['attendance']['late'] else 0 for _, hist in self.mems.items())


		self.summary['stat']['present'] = '{}/{}'.format(present, total)
		self.summary['stat']['dropouts'] = '{}/{}'.format(dropouts, total)
		self.summary['stat']['earlyLeaves'] = '{}/{}'.format(earlyLeaves, total)
		self.summary['stat']['lates'] = '{}/{}'.format(lates, total)
		self.summary['stat']['absent'] = '{}/{}'.format(len(absence), total)
		self.summary['absent'] = absence


class AttendanceChecker:
	def __init__(self, memberList, config):
		self.config = config
		self.sheet = AttendancSheet(config)

		self.memberList = memberList
		self.lastCheck = None
		self.toDtm = lambda _str: datetime.strptime(str(config.startTime.date()) + '-' + _str, '%Y-%m-%d-%H:%M:%S')

	def filterRecords(updateFn):
		def wrapper(self, newRec):
			filtered = []
			for rec in newRec:
				dtime, name = self.toDtm(rec['time']), rec['name']

				if self.lastCheck and dtime <= self.lastCheck:
					# skip old records
					continue
				if name.startswith('澳'):
					# skip Australian mates, coz they are treated specially :D
					continue
				if name not in self.memberList:
					# take note of unrecognised name and skip them
					self.sheet.summary['unrecognised'].add(name)
					continue
				filtered.append(rec)

			updateFn(self, filtered)
			self.lastCheck = self.toDtm(newRec[-1]['time'])

		return wrapper

	@filterRecords
	def updateSheet(self, newRec):
		for rec in newRec:
			dtime, action, name = self.toDtm(rec['time']), rec['action'], rec['name']

			if name not in self.sheet.mems:
				# create new entry for members not yet in the attendance sheet
				self.sheet.signin(name)

			# mark every enter and leave, and do the attendance check.
			if action == '进入':
				self.sheet.memEnter(name, dtime)
			elif action == '退出':
				self.sheet.memLeave(name, dtime)

	def conclude(self):
		self.sheet.conclude(self.memberList)
