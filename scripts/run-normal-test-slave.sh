#!/bin/bash

CUR_NODE=${1:-0}

for ((i=8;i<=14;i++)); do
    echo "./scripts/run-project-pactum-docker-slave $CUR_NODE $i $i"
    ./scripts/run-project-pactum-docker-slave $CUR_NODE $i $i
done