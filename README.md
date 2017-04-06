## 海外研讨班考勤辅助

**Python版本**： ^3.5.2

**第三方依赖库**： 暂无



#### 功能说明：

考勤辅助系统的第一期代码。 当前实现功能如下：

1. 读取TXT格式的YY进出记录（可次第读取多个文件中的记录）
2. 判断各学员的出勤情况，包括了迟到、早退，以及中途不在频道时间超过15分钟。
3. 输出考勤结果到csv，包含
   1. 出勤、早退、迟到、长期退出的统计。
   2. 每个学员的考勤结果及其进出房间记录。 
   3. 未识别人员



#### 测试说明：

* 将Main.py主函数部分指调用test方法，其他注释掉， 然后可根据自己的文件目录修改test放下的config参数。



#### TODO：

* 单元测试？
* 自动化获取YY进出记录？



## Change Log

**0.0.1**: 第一阶段需求和UI完成；

**0.0.2**: 加强对输入文件的编码检测。[15d4e36](https://github.com/namoshizun/AttendanceChecker/commit/15d4e363f1415731d5f6fb9365570a8b59a569d9)

**0.0.3**: 修改输出csv的编码方案为'utf-8-sig'以应对excel乱码问题； 输出结果中根据出勤情况排序 [13c19a2](https://github.com/namoshizun/AttendanceChecker/commit/13c19a2ab2afaa7f19e75566e1c7ad9b11dc6a04) [fb97912](https://github.com/namoshizun/AttendanceChecker/commit/fb9791214182711744719b720d2c928cfd039022)
