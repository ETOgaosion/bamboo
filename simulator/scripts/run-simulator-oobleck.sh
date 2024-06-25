#!/bin/bash

mkdir -p res/simuitest-oobleck-p3
mkdir -p res/simuitest-oobleck-g4dn

python -m simulation_oobleck --model-size '350M' --generate-graphs --spot-instance-trace traces/p3-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-oobleck-p3 > simu.txt 2>&1
python -m simulation_oobleck --model-size '350M'  --generate-graphs --spot-instance-trace traces/g4dn-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-oobleck-g4dn > simu.txt 2>&1

# python -m simulation_oobleck --model-size '1.3B' --generate-graphs --spot-instance-trace traces/p3-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-oobleck-p3 > simu.txt 2>&1
# python -m simulation_oobleck --model-size '1.3B'  --generate-graphs --spot-instance-trace traces/g4dn-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-oobleck-g4dn > simu.txt 2>&1

# python -m simulation_oobleck --model-size '2.7B' --generate-graphs --spot-instance-trace traces/p3-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-oobleck-p3 > simu.txt 2>&1
# python -m simulation_oobleck --model-size '2.7B'  --generate-graphs --spot-instance-trace traces/g4dn-trace-8-24.csv --model GPT-3 --fig-directory res/simuitest-oobleck-g4dn > simu.txt 2>&1

# python -m simulation --generate-graphs --model GPT-2 --fig-directory res/simuitest-no-trace > simu.txt 2>&1