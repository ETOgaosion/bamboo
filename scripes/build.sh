#!/bin/bash

target=${1:-0}

if [ $target -eq 0 ]; then
    echo "build bamboo image"
    docker build -t whatcanyousee/bamboo:latest .
else
    echo "build base image"
    docker build -t whatcanyousee/bamboo-base:latest -f Dockerfile.base .
fi