#!/bin/bash

# make sure conda env is BambooRes or BambooSimulator (use requirements file to initialize)
# Usage: python -m test.bambootest [-h] [--plot-each] [--plot-avg] [--plot-dec] [--plot-layer] [--calculate-rdzv] [--calculate-fallback] [--calculate-pipeline-delta] [--base-dir BASE_DIR]

python -m test.bambootest --calculate-rdzv