#!/bin/bash

python -m simulation --generate-graphs --spot-instance-trace traces/p3-trace-16.csv --model GPT-3 --fig-directory res/simuitest > simu.txt 2>&1

# python -m simulation --generate-graphs --model GPT-2 --fig-directory res/simuitest-no-trace > simu.txt 2>&1