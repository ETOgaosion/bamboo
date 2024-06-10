#!/bin/bash

target="91 92 46"

for ip in $target; do
    rm -rf /home/gaoziyuan/project/bamboo/res/others/$ip
    scp -r zkyd-$ip:/home/gaoziyuan/project/bamboo/res/lab /home/gaoziyuan/project/bamboo/res/others/$ip
done