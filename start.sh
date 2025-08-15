#!/bin/bash
#Linux平台启动入口

# clear

is_restart=1

while (($is_restart))
do
 stty echo
 poetry run python main.py
 is_restart=$?
done
stty echo
