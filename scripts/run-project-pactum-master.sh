#!/bin/bash

CURRENT_PATH=$(pwd)

NUM_NODES=${1:-8}
NUM_STAGES=${2:-8}
GLOBAL_RANK=${3}
MICRO_BATCH_SIZE=${4:-2}
SEQ_LEN=${5:-1024}
NUM_NODES_MIN=${1:-$NUM_NODES}
LAYERS=${6:-24}
RDZV_IP=${7:-localhost}
ID=encoder${8}

MODEL=${CURRENT_PATH}/project_pactum/external/deepspeed/DeepSpeedExamples/pipeline_parallelism/gpt3

echo "ARGS $RDZV_IP $ID $NUM_STAGES $GLOBAL_RANK $MODEL"

cmd="""export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
	export NCCL_SOCKET_IFNAME=enp216s0np0 \
	export GLOBAL_RANK=$GLOBAL_RANK \
	export PYTHONPATH=${CURRENT_PATH}/project-pactum:\${PYTHONPATH} && \
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
	-s 3 \
	--seq=$SEQ_LEN \
	-N ${LAYERS} \
	--nodes=${NUM_NODES} \
	--backend=nccl \
	--redundancy_level=1 \
	${@:9} \
	--deepspeed \
	--deepspeed_config ${MODEL}_${MICRO_BATCH_SIZE}.json"""

echo "RUNNING CMD $cmd"

eval $cmd