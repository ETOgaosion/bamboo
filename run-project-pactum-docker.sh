#!/bin/bash

CUR_NODE=${1:-0}

if [ $CUR_NODE -eq 0 ]; then
    echo "Running on master node"
    docker build -t whatcanyousee/bamboo:latest .
    etcdctl rm --dir --recursive /torchelastic
fi

cmd="""docker run --rm -it --net "host" --gpus 'device=$CUR_NODE' -w '/workspace' whatcanyousee/bamboo \
    /bin/bash -c './run-project-pactum.sh'"""

echo "RUNNING CMD $cmd"

eval $cmd