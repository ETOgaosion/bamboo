#!/bin/bash

CUR_NODE=${1:-0}
NUM_NODES=${2:-16}
NUM_STAGES=${3:-16}
GLOBAL_RANK=${4}
MICRO_BATCH_SIZE=${5:-8}
SEQ_LEN=${6:-512}
LAYERS=${7:-24}
# REBUILD=${6}

# if [ $CUR_NODE -eq 0 ]; then
#     echo "Running on master node"
#     if [ $REBUILD -eq 1 ]; then
#         docker build -t whatcanyousee/bamboo:latest .
#     fi
#     # etcdctl rm --dir --recursive /torchelastic
# fi

mkdir -p "res/lab/nodes_$NUM_NODES_$NUM_STAGES"

cmd="""docker run --net "host" --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
    /bin/bash -c './scripts/run-project-pactum-master.sh $NUM_NODES $NUM_STAGES $GLOBAL_RANK $MICRO_BATCH_SIZE $SEQ_LEN $LAYERS' > res/lab/nodes_$NUM_NODES_$NUM_STAGES/node_$CUR_NODE.txt 2>&1"""

# cmd="""docker run --rm -it --net "host" --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
#     /bin/bash -c './scripts/run-project-pactum-master.sh $NUM_NODES $NUM_STAGES'"""

echo "RUNNING CMD $cmd"

eval $cmd