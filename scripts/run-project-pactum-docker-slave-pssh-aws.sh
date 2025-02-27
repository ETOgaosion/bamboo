#!/bin/bash

CUR_NODE=${1:-0}
NUM_NODES=${2:-16}
NUM_STAGES=${3:-16}
GLOBAL_RANK=${4}
MICRO_BATCH_SIZE=${5:-8}
SEQ_LEN=${6:-2048}
MODEL_SIZE=${7:-"350M"}
LAYERS=${8:-24}
# REBUILD=${6}

# if [ $CUR_NODE -eq 0 ]; then
#     echo "Running on slave node"
#     if [ $REBUILD -eq 1 ]; then
#         docker build -t whatcanyousee/bamboo:latest .
#     fi
# fi

mkdir -p "res/lab_aws/${MODEL_SIZE}/nodes_${NUM_NODES}_${NUM_STAGES}_${MICRO_BATCH_SIZE}"


source ~/.bashrc && export CUDA_VISIBLE_DEVICES=$CUR_NODE && export NCCL_SOCKET_IFNAME=ens5 && export GLOO_SOCKET_IFNAME=ens5 && \
export LD_PRELOAD=/usr/local/cuda-11.7/efa/lib/libnccl-net.so && export LD_LIBRARY_PATH=/usr/local/cuda-11.7/efa/lib/:\$LD_LIBRARY_PATH && \
./scripts/run-project-pactum-slave.sh $NUM_NODES $NUM_STAGES $GLOBAL_RANK $MICRO_BATCH_SIZE $SEQ_LEN $LAYERS $MODEL_SIZE' > res/lab_aws/${MODEL_SIZE}//nodes_${NUM_NODES}_${NUM_STAGES}_${MICRO_BATCH_SIZE}/node_$CUR_NODE.txt 2>&1