#!/bin/bash

# python -m project_pactum.simulation --generate-graphs --spot-instance-trace traces/p3-trace.csv --model GPT-2 --fig-directory res/simuitest > simu.txt 2>&1

python -m project_pactum.simulation --generate-graphs --model GPT-2 --fig-directory res/simuitest-no-trace > simu.txt 2>&1