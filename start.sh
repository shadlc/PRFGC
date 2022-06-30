#!/bin/bash
#Linux平台启动入口

clear
stty echo

is_restart=1

while (($is_restart))
do
 python3 robot.py
 is_restart=$?
done

stty echo