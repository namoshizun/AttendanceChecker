import re, json, sys, itertools
import os, csv, codecs
from datetime import datetime, timedelta
from itertools import chain, zip_longest
from functools import reduce
from .util import load_workbook, save_workbook

MAX_TIME = datetime.now() + timedelta(9999)
THRESHOLD = timedelta(minutes=15)

class UserParams:
    def __init__(self, options):
        self.__attach__(options)

    def __attach__(self, newProps):
        for key, value in newProps.items():
            self.__dict__[key] = value
        return self


class CheckerUtil:
    def __init__(self, params):
        self.params = params
        self.regex = re.compile(r"[^[]*\[([^]]*)\] (进入|退出) [^[]*\[([^]]*)\] 频道。\((.*?)\)")

    def __lines_to_dict(self, lines):
        ret = []
        for line in lines:
            match = self.regex.findall(line)
            if len(match) == 1:
                _ = match[0]
                ret.append({
                    'name': _[0],
                    'action': _[1],
                    'time': _[3]
                })
        return ret

    def synthesise_record(self, startNames, endNames):
        """
        mock-up the YY chatboard record data that can be immediately read by attendance checker.
        """
        startNames, endNames = set(startNames), set(endNames)
        lines, params = [], self.params
        startTime, endTime = params.startTime, params.startTime + timedelta(minutes=params.classLength[0]*60+params.classLength[1])
        earlyLeaveTime = endTime - (THRESHOLD + timedelta(minutes=1))
        lateEnterTIme = startTime + (THRESHOLD + timedelta(minutes=1))
        template = '通知： [{name}] {action} [法义辅导] 频道。({time})'

        # partition into lates, eariers and normal
        earlyLeaves = startNames.difference(endNames)
        lateEnters = endNames.difference(startNames)
        normal = startNames.intersection(endNames)

        # make lines accordingly
        list(map(lambda name: lines.append(template.format(name=name, action='进入', time=datetime.strftime(startTime, '%H:%M:%S'))), normal))
        list(map(lambda name: lines.append(template.format(name=name, action='进入', time=datetime.strftime(lateEnterTIme, '%H:%M:%S'))), lateEnters))
        list(map(lambda name: lines.append(template.format(name=name, action='退出', time=datetime.strftime(earlyLeaveTime, '%H:%M:%S'))), earlyLeaves))
        
        with open('./tmp.txt', 'w+') as tmp:
            tmp.writelines(lines)
        return self.__lines_to_dict(lines)


class MemberSheet:
    def __init__(self, source):
        self.data = load_workbook(source)
        self.source = source
    
    @property
    def members(self):
        return set(itertools.chain.from_iterable([v.index.values for k, v in self.data.items()]))

    def from_attendance_sheet(self, sheet):
        def mark(name, earlyLeave=False, late=False):
            for region, df in self.data.items():
                if name not in df.index:
                    continue
                if earlyLeave or late:
                    df.loc[name, 2] = '早退' if earlyLeave else '迟到'
                else:
                    df.loc[name, 3] = '全勤'

        for name, stats in sheet.mems.items():
            mark(name, **stats['attendance'])
    
    def refresh(self, backup=False):
        # if backup:
        #     os.rename(self.source, 'backup')
        os.remove(self.source)
        save_workbook(self)


class AttendancSheet:
    def __init__(self, params):
        endTime = params.startTime + timedelta(minutes=params.classLength[0]*60+params.classLength[1])
        self.summary = {
            'stat': {
                'present': None,
                'earlyLeaves': None,
                'lates': None,
                'absent': None,
            },
            'absent': None,
            'period': [params.startTime, endTime],
        }
        self.mems = {}

    def signin(self, name):
        self.mems[name] = {
            'enter': [],
            'leave': [],
            'attendance': {'late': False, 'earlyLeave': False }
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

    def conclude(self, members):
        present, earlyLeaves, lates, total = 0, 0, 0, len(members)
        start, end = self.summary['period'][0], self.summary['period'][1]
        absence = list(members - set(self.mems.keys()))

        for mem, hist in self.mems.items():
            pairs = list(zip(hist['enter'], hist['leave']))

            # first enter - start > treshold
            if pairs[0][0] > start and (pairs[0][0] - start) > THRESHOLD:
                self.mems[mem]['attendance']['late'] = True
                lates += 1

            # end - last leave > treshold
            if end > pairs[-1][1] and (end - pairs[-1][1]).seconds > THRESHOLD:
                self.mems[mem]['attendance']['earlyLeave'] = True
                earlyLeaves += 1

        present = sum(int(not hist['attendance']['earlyLeave'] and not hist['attendance']['late']) for _, hist in self.mems.items())

        self.summary['stat']['present'] = '{}/{}'.format(present, total)
        self.summary['stat']['earlyLeaves'] = '{}/{}'.format(earlyLeaves, total)
        self.summary['stat']['lates'] = '{}/{}'.format(lates, total)
        self.summary['stat']['absent'] = '{}/{}'.format(len(absence), total)
        self.summary['absent'] = absence


class AttendanceChecker:
    def __init__(self, params):
        self.sheet = AttendancSheet(params)
        self.lastCheck = None
        self.to_datetime = lambda _str: datetime.strptime(str(params.startTime.date()) + '-' + _str, '%Y-%m-%d-%H:%M:%S')

    def update_sheet(self, newRec):
        for rec in newRec:
            dtime, action, name = self.to_datetime(rec['time']), rec['action'], rec['name']

            if name not in self.sheet.mems:
                # create new entry for members not yet in the attendance sheet
                self.sheet.signin(name)

            # mark every enter and leave, and do the attendance check.
            if action == '进入':
                self.sheet.memEnter(name, dtime)
            elif action == '退出':
                self.sheet.memLeave(name, dtime)

    def conclude(self, member_sheet):
        self.sheet.conclude(member_sheet.members)
        member_sheet.from_attendance_sheet(self.sheet)
