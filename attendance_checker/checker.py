import re, json, sys, itertools
import os, csv
import pandas as pd
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
        startTime, endTime = params.startTime, params.startTime + timedelta(hours=2)
        earlyLeaveTime = endTime - (THRESHOLD + timedelta(minutes=1))
        lateEnterTIme = startTime + (THRESHOLD + timedelta(minutes=1))
        template = '通知： [{name}] {action} [法义辅导] 频道。({time})'

        # partition into lates and early leaves
        earlyLeaves = startNames.difference(endNames)
        lateEnters = endNames.difference(startNames)

        print('early leaves: {}'.format(earlyLeaves))
        print('late enters: {}'.format(lateEnters))

        # make lines accordingly --- order matters a lot !!!
        list(map(lambda name: lines.append(template.format(name=name, action='进入', time=datetime.strftime(startTime, '%H:%M:%S'))), startNames))
        list(map(lambda name: lines.append(template.format(name=name, action='进入', time=datetime.strftime(lateEnterTIme, '%H:%M:%S'))), lateEnters))
        list(map(lambda name: lines.append(template.format(name=name, action='退出', time=datetime.strftime(earlyLeaveTime, '%H:%M:%S'))), earlyLeaves))
        list(map(lambda name: lines.append(template.format(name=name, action='退出', time=datetime.strftime(endTime, '%H:%M:%S'))), endNames))
        
        return self.__lines_to_dict(lines)


class MemberSheet:
    def __init__(self, source):
        self.data = load_workbook(source)
        self.source = source
    
    @property
    def members(self):
        return set(itertools.chain.from_iterable([v.index.values for k, v in self.data.items()]))

    def from_attendance_sheet(self, sheet):
        def mark(yy_name, earlyLeave=False, late=False):
            marked = False
            for region, df in self.data.items():
                if yy_name not in df.index:
                    continue
                
                df.loc[yy_name, '截屏1'] = int(not late)
                df.loc[yy_name, '截屏2'] = int(not earlyLeave)
                df.loc[yy_name, '结果'] = int(not earlyLeave and not late)
                
                if earlyLeave or late:
                    idx = len(unattended)
                    unattended.loc[idx] = [df.loc[yy_name, '姓名'], yy_name, region, '缺勤', '早退' if earlyLeave else '迟到']
                
                marked = True
            
            return None if marked else yy_name

        def extract_unattended():
            counter = 0
            unattended = pd.DataFrame(columns=['姓名', 'YY昵称', '地区', '出勤情况', '备注'])
            for region, df in self.data.items():
                for yy_name, row in df.iterrows():
                    if row['结果'] == 0:
                        unattended.loc[counter] = [row['姓名'], yy_name, region,
                                                   '缺勤', '早退' if row['截屏2'] == 0 else '迟到' if row['截屏1'] == 0 else '']
                        counter += 1
            return unattended
        
        not_marked = [mark(name, **stats['attendance']) for name, stats in sheet.mems.items()]
        self.data['缺勤'] = extract_unattended()        
        return list(filter(bool, not_marked))
    
    def refresh(self, backup=False):
        # pass
        os.remove(self.source)
        save_workbook(self)


class AttendancSheet:
    """
    Note: many functions are inherited from legacy system
    """
    def __init__(self, params):
        endTime = params.startTime + timedelta(hours=2)
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
            if pairs[0][0] > start and (pairs[0][0] - start) >= THRESHOLD:
                self.mems[mem]['attendance']['late'] = True
                lates += 1

            # end - last leave > treshold
            if end > pairs[-1][1] and (end - pairs[-1][1]) >= THRESHOLD:
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
        not_marked = member_sheet.from_attendance_sheet(self.sheet)
        return not_marked
