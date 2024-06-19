#!/bin/bash

CURRENT_PATH=$(pwd)

NUM_NODES=${1:-16}
NUM_STAGES=${2:-16}
GLOBAL_RANK=${3}
MICRO_BATCH_SIZE=${4:-8}
SEQ_LEN=${5:-512}
RDZV_IP=${6:-localhost}
ID=encoder${7}

MODEL=${CURRENT_PATH}/project_pactum/external/deepspeed/DeepSpeedExamples/pipeline_parallelism/gpt3

echo "ARGS $RDZV_IP $ID $NUM_STAGES $GLOBAL_RANK $MODEL"

cmd="""export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
	export NCCL_SOCKET_IFNAME=eno1 \
	export USE_BARRIER=true \
	export GLOBAL_RANK=$GLOBAL_RANK \
	export PYTHONPATH=${CURRENT_PATH}/project-pactum:\${PYTHONPATH} && \
	python -m project_pactum.run \
	--rdzv_backend=etcd-v2 \
	--rdzv_endpoint=$RDZV_IP:2379 \
	--rdzv_id=$ID \
	--nnodes=2:$NUM_NODES \
	--nproc_per_node=1 \
	--project-pactum \
	--max-pipe-parallel-size=24 \
	--default-num-stages=${NUM_STAGES} \
	${MODEL}.py \
	-s 4 \
	--seq=${SEQ_LEN} \
	--stages=${NUM_STAGES} \
	--backend=nccl \
	--redundancy_level=1 \
	${@:8} \
	--deepspeed \
	--deepspeed_config ${MODEL}_${MICRO_BATCH_SIZE}.json"""

echo "RUNNING CMD $cmd"

eval $cmd