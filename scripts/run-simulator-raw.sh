#!/bin/bash

python -m project_pactum.simulation_raw --generate-graphs --spot-instance-trace traces/p3-trace.csv --model GPT-2 > simu.txt 2>&1