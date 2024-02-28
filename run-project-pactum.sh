#!/bin/bash

CURRENT_PATH=$(pwd)

RDZV_IP=${1:-localhost}
ID=encoder${2}
NUM_STAGES=${3}
NUM_STAGES=${NUM_STAGES:-4}

MODEL=${CURRENT_PATH}/project-pactum/external/deepspeed/DeepSpeedExamples/pipeline_parallelism/transformer

echo "ARGS $RDZV_IP $ID $NUM_STAGES $MODEL"

cmd="""export PROJECT_PACTUM_LOGGING_WARNING='etcd.client,etcd.lock,torch.distributed.distributed_c10d' \
	&& \
	export PYTHONPATH=${CURRENT_PATH}/project-pactum:\${PYTHONPATH} \
	&& \
	python -m pdb -m project_pactum.run \
	--rdzv_backend=etcd-v2 \
	--rdzv_endpoint=$RDZV_IP:2379 \
	--rdzv_id=$ID \
	--nnodes=1:64 \
	--nproc_per_node=1 \
	--project-pactum \
	--max-pipe-parallel-size=24 \
	--default-num-stages=${NUM_STAGES} \
	${MODEL}.py \
	--backend=nccl \
	--redundancy_level=1 \
	${@:5} \
	--deepspeed \
	--deepspeed_config ${MODEL}.json"""

echo "RUNNING CMD $cmd"

eval $cmd