#!/bin/bash

CURRENT_PATH=$(pwd)

NUM_NODES=${1:-16}
NUM_STAGES=${2:-16}
GLOBAL_RANK=${3}
MICRO_BATCH_SIZE=${4:-8}
SEQ_LEN=${5:-1024}
NUM_NODES_MIN=${1:-$NUM_NODES}
LAYERS=${6:-24}
$MODEL_SIZE=${7:-"350M"}
RDZV_IP=${8:-172.31.45.44}
ID=encoder${9}

MODEL=${CURRENT_PATH}/project_pactum/external/deepspeed/DeepSpeedExamples/pipeline_parallelism/gpt3

echo "ARGS $RDZV_IP $ID $NUM_STAGES $GLOBAL_RANK $MODEL"

source ~/.bashrc

echo "CUDA_VISIBLE_DEVICES $CUDA_VISIBLE_DEVICES NCCL_DEBUG $NCCL_DEBUG NCCL_SOCKET_IFNAME $NCCL_SOCKET_IFNAME GLOO_SOCKET_IFNAME $GLOO_SOCKET_IFNAME LD_PRELOAD $LD_PRELOAD LD_LIBRARY_PATH $LD_LIBRARY_PATH" && \

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
export PYTHONPATH=${CURRENT_PATH}:\${PYTHONPATH} \
export GLOBAL_RANK=$GLOBAL_RANK && \
python -m project_pactum.run \
	--rdzv_backend=etcd-v2 \
	--rdzv_endpoint=$RDZV_IP:2379 \
	--rdzv_id=$ID \
	--nnodes=$NUM_NODES:$NUM_NODES \
	--nproc_per_node=1 \
	--project-pactum \
	--max-pipe-parallel-size=24 \
	--default-num-stages=${NUM_STAGES} \
	${MODEL}.py \
	-s 5 \
	--seq=$SEQ_LEN \
	-N ${LAYERS} \
	--nodes=${NUM_NODES} \
	--backend=nccl \
	--redundancy_level=1 \
	--model-size="$MODEL_SIZE" \
	${@:10} \
	--deepspeed \
	--deepspeed_config ${MODEL}_${MICRO_BATCH_SIZE}.json