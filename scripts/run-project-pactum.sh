#!/bin/bash

CURRENT_PATH=$(pwd)


NUM_NODES=${1:-8}
NUM_STAGES=${2:-4}
RDZV_IP=${3:-3.138.118.213}
ID=encoder${4}

MODEL=${CURRENT_PATH}/project_pactum/external/deepspeed/DeepSpeedExamples/pipeline_parallelism/gpt2

echo "ARGS $RDZV_IP $ID $NUM_STAGES $MODEL"

ip a

cmd="""export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
	export USE_BARRIER=true \
	&& \
	export PYTHONPATH=${CURRENT_PATH}/project-pactum:\${PYTHONPATH} \
	&& \
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
	-s 50 \
	--backend=nccl \
	--redundancy_level=1 \
	${@:5} \
	--deepspeed \
	--deepspeed_config ${MODEL}.json"""

echo "RUNNING CMD $cmd"

eval $cmd