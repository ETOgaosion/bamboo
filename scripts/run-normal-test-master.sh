#!/bin/bash

CUR_NODE=${1:-0}

for ((i=8;i<=14;i++)); do
    echo "./run-project-pactum-docker-master $CUR_NODE $i $i"
    ./run-project-pactum-docker-master $CUR_NODE $i $i
done