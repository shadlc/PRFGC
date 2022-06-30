#!/usr/bin/python
#print使用的颜色变量

import platform

SYSTEM_PLATFORM = platform.system()
#如果使用Windows自带的命令提示符无法支持颜色效果
if SYSTEM_PLATFORM == 'Windows':
	RESET = ''
	BLACK = ''
	RED = ''
	LRED = ''
	GREEN = ''
	LGREEN = ''
	YELLOW = ''
	LYELLOW = ''
	BLUE = ''
	LBLUE = ''
	PURPLE = ''
	LPURPLE = ''
	CYAN = ''
	LCYAN = ''
	GREY = ''
	WHITE = ''

else:
	RESET = '\033[0m'
	BLACK = '\033[0;30m'
	RED = '\033[0;31m'
	LRED = '\033[1;31m'
	GREEN = '\033[0;32m'
	LGREEN = '\033[1;32m'
	YELLOW = '\033[0;33m'
	LYELLOW = '\033[1;33m'
	BLUE = '\033[0;34m'
	LBLUE = '\033[1;34m'
	PURPLE = '\033[0;35m'
	LPURPLE = '\033[1;35m'
	CYAN = '\033[0;36m'
	LCYAN = '\033[1;36m'
	GREY = '\033[0;37m'
	WHITE = '\033[1;37m'

#提供全部颜色的数列
ALL_COLOR = [BLACK,RED,LRED,GREEN,LGREEN,YELLOW,LYELLOW,BLUE,LBLUE,PURPLE,LPURPLE,CYAN,LCYAN,GREY,WHITE]