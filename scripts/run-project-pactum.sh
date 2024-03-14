#!/bin/bash

CURRENT_PATH=$(pwd)

NUM_NODES=${1:-7}
NUM_STAGES=${2:-2}
RDZV_IP=${3:-localhost}
ID=encoder${4}

MODEL=${CURRENT_PATH}/project_pactum/external/deepspeed/DeepSpeedExamples/pipeline_parallelism/transformer

echo "ARGS $RDZV_IP $ID $NUM_STAGES $MODEL"

ip a

cmd="""export PROJECT_PACTUM_LOGGING_INFO='etcd.client,etcd.lock,torch.distributed.distributed_c10d' \
	export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
	export LOGLEVEL=INFO \
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