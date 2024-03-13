#!/bin/bash

WAY=${1}
MODEL=${2}

ulimit -m 209715200

if [ $WAY -eq 1 ]; then
    python -m project_pactum.simulation --generate-table --model $MODEL
else
    python -m project_pactum.simulation --generate-graphs --model $MODEL
fi