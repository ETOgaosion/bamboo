#!/bin/bash

CUR_NODE=${1:-0}
NUM_NODES=${2:-16}
NUM_STAGES=${3:-16}
GLOBAL_RANK=${4}
REBUILD=${5}
MICRO_BATCH_SIZE=${6:-8}

if [ $CUR_NODE -eq 0 ]; then
    echo "Running on slave node"
    if [ $REBUILD -eq 1 ]; then
        docker build -t whatcanyousee/bamboo:latest .
    fi
fi

mkdir -p "res/lab/nodes_$NUM_NODES"

cmd="""docker run -it --net "host" --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
    /bin/bash -c './scripts/run-project-pactum-slave.sh $NUM_NODES $NUM_STAGES $GLOBAL_RANK $MICRO_BATCH_SIZE' > res/lab/nodes_$NUM_NODES/node_$CUR_NODE.txt 2>&1"""

# cmd="""docker run --rm -it --net "host" --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
#     /bin/bash -c './scripts/run-project-pactum-slave.sh $NUM_NODES $NUM_STAGES'"""

echo "RUNNING CMD $cmd"

eval $cmd