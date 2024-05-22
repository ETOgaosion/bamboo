#!/bin/bash

CUR_NODE=${1:-0}
NUM_NODES=${2:-16}
NUM_STAGES=${3:-16}
SUBNBET=${4}

if [ $CUR_NODE -eq 0 ]; then
    echo "Running on master node"
    docker build -t whatcanyousee/bamboo:latest .
    etcdctl rm --dir --recursive /torchelastic
fi

mkdir -p "res/lab/nodes_append"

cmd="""docker run -it --net iptastic --ip 172.0.$SUBNBET.$CUR_NODE --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
    /bin/bash -c './scripts/run-project-pactum-master.sh $NUM_NODES $NUM_STAGES' > res/lab/nodes_append/node_$CUR_NODE.txt 2>&1"""

# cmd="""docker run --rm -it --net "host" --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
#     /bin/bash -c './scripts/run-project-pactum-master.sh $NUM_NODES $NUM_STAGES'"""

echo "RUNNING CMD $cmd"

eval $cmd