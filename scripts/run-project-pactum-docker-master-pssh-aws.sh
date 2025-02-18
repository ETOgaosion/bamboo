#!/bin/bash

CUR_NODE=${1:-0}
NUM_NODES=${2:-16}
NUM_STAGES=${3:-16}
GLOBAL_RANK=${4}
MICRO_BATCH_SIZE=${5:-8}
SEQ_LEN=${6:-2048}
LAYERS=${7:-24}
# REBUILD=${6}

# if [ $CUR_NODE -eq 0 ]; then
#     echo "Running on master node"
#     if [ $REBUILD -eq 1 ]; then
#         docker build -t whatcanyousee/bamboo:latest .
#     fi
    # etcdctl rm --dir --recursive /torchelastic
# fi

mkdir -p "res/lab_aws/nodes_${NUM_NODES}_${NUM_STAGES}_${MICRO_BATCH_SIZE}"

cmd="""export CUDA_VISIBLE_DEVICES=$CUR_NODE && export NCCL_DEBUG=INFO && export NCCL_SOCKET_IFNAME=ens5 && export GLOO_SOCKET_IFNAME=ens5 && \
    export LD_PRELOAD=/usr/local/cuda-11.7/efa/lib/libnccl-net.so && export LD_LIBRARY_PATH=/usr/local/cuda-11.7/efa/lib/:$LD_LIBRARY_PATH && \
    ./scripts/run-project-pactum-master.sh $NUM_NODES $NUM_STAGES $GLOBAL_RANK $MICRO_BATCH_SIZE $SEQ_LEN $LAYERS > res/lab_aws/nodes_${NUM_NODES}_${NUM_STAGES}_${MICRO_BATCH_SIZE}/node_$CUR_NODE.txt 2>&1"""

# cmd="""docker run --rm -it --net "host" --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
#     /bin/bash -c './scripts/run-project-pactum-master.sh $NUM_NODES $NUM_STAGES'"""

echo "RUNNING CMD $cmd"

eval $cmd