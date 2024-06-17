#!/bin/bash

python -m simulator.simulation --generate-graphs --spot-instance-trace simulator/traces/p3-trace-16.csv --model GPT-3 --fig-directory simulator/res/simuitest > simu.txt 2>&1

# python -m simulator.simulation --generate-graphs --model GPT-2 --fig-directory simulator/res/simuitest-no-trace > simu.txt 2>&1