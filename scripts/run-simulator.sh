#!/bin/bash

WAY=${1}
MODEL=${2}
TRACE=${3:-"trace/p3-trace.csv"}

ulimit -m 209715200

if [ $WAY -eq 1 ]; then
    python -m project_pactum.simulation --generate-table --spot-instance-trace $TRACE --model $MODEL
else
    python -m project_pactum.simulation --generate-graphs --spot-instance-trace $TRACE --model $MODEL
fi