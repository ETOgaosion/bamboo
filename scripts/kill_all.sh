#!/bin/bash
addrs=(10.20.23.91 10.20.23.92 10.20.23.46 10.20.23.42 10.20.23.47)
for addr in "${addrs[@]}"; do
    ssh -p ${port} ${addr} "cd /home/gaoziyuan/project/bamboo && ./scripts/kill.sh" 
done