#!/bin/bash

mkdir -p res/simuitest-varu-p3
mkdir -p res/simuitest-varu-g4dn

python -m simulation_varu --generate-graphs --spot-instance-trace traces/p3-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-varu-p3 > simu.txt 2>&1
python -m simulation_varu --generate-graphs --spot-instance-trace traces/p3-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-varu-g4dn > simu.txt 2>&1

# python -m simulation --generate-graphs --model GPT-2 --fig-directory res/simuitest-no-trace > simu.txt 2>&1