#!/bin/bash

CURRENT_PATH=$(pwd)

NUM_NODES=${1:-8}
NUM_STAGES=${2:-8}
GLOBAL_RANK=${3}
MICRO_BATCH_SIZE=${4:-2}
SEQ_LEN=${5:-2048}
LAYERS=${6:-24}
RDZV_IP=${7:-localhost}
ID=encoder${8}

MODEL=${CURRENT_PATH}/project_pactum/external/deepspeed/DeepSpeedExamples/pipeline_parallelism/gpt3

echo "ARGS $RDZV_IP $ID $NUM_STAGES $GLOBAL_RANK $MODEL"

cmd="""export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
	export NCCL_SOCKET_IFNAME=ens5 \
	export LD_LIBRARY_PATH=/opt/nccl/build/lib:/usr/local/cuda/lib64:/opt/amazon/efa/lib:/opt/amazon/openmpi/lib:/opt/aws-ofi-nccl/lib:$LD_LIBRARY_PATH \
	export FI_EFA_USE_DEVICE_RDMA=1 \
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
	-N ${LAYERS} \
	--nodes=${NUM_NODES} \
	--backend=nccl \
	--redundancy_level=1 \
	${@:9} \
	--deepspeed \
	--deepspeed_config ${MODEL}_${MICRO_BATCH_SIZE}.json"""

echo "RUNNING CMD $cmd"

eval $cmd