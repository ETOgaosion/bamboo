import os
import random
import re
from dateutil import parser as dateparser
import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import statistics
import statsmodels.api as sm
import numpy as np
from itertools import chain
import pprint
import math
import json

# valid file
valid_file = re.compile(r'node_\d+\.log')
# judge the log line
is_log_parser = re.compile(r'\[ \d{2,}\|\d{2,} \]')
# extract the time
time_parser = re.compile(r'(?P<time>\d{4,}-\d{2,}-\d{2,} \d{2,}:\d{2,}:\d{2,}.\d+)')
# extract the batch operation
start_batch_parser                  = re.compile(r'START BATCH (?P<batchid>\d+)')
finish_batch_parser                 = re.compile(r'FINISH BATCH (?P<batchid>\d+) took (?P<batchtime>\S+) s')
start_local_model_train_parser      = re.compile(r'START LOCAL MODEL TRAIN (?P<globalstep>\d+)')
finish_local_model_train_parser     = re.compile(r'FINISH LOCAL MODEL TRAIN (?P<globalstep>\d+)')
failure_node_detect_parser          = re.compile(r'\[Engine\] Signal handler called with signal 15')
# extract the failure
failure_detect_parser               = re.compile(r'FAILURES')
# extract the exception
start_next_stage_exception_parser   = re.compile(r'START NextStageException fallback schedule (?P<globalstep>\d+)')
finish_next_stage_exception_parser  = re.compile(r'FINISH NextStageException fallback schedule (?P<globalstep>\d+)')
start_prev_stage_exception_parser   = re.compile(r'START PrevStageException fallback schedule (?P<globalstep>\d+)')
finish_prev_stage_exception_parser  = re.compile(r'FINISH PrevStageException fallback schedule (?P<globalstep>\d+)')
# extract the reconfigure
start_reconfigure_parser            = re.compile(r'START RECONFIGURE (?P<globalstep>\d+)')
finish_save_shadow_node_parser      = re.compile(r'FINISH SAVE SHADOW NODE STATE (?P<globalstep>\d+)')
start_reconfigure_cluster_parser    = re.compile(r'START RECONFIGURE CLUSTER and TRANSFER LAYERS (?P<globalstep>\d+)')
finish_reconfigure_parser           = re.compile(r'FINISH RECONFIGURE (?P<globalstep>\d+)')
layer_counter_parser                = re.compile(r'layer num: (?P<layer>\d+)')

start_schedule_parser               = re.compile(r'START FIRST TRY TO SCHEDULE (?P<globalstep>\d+)')
finish_schedule_parser              = re.compile(r'FINISH FIRST TRY TO SCHEDULE (?P<globalstep>\d+)')
cmd_parser                          = re.compile(r'Execute step (?P<cmdstep>\d+) Command (?P<cmd>\w+)')

global_rank_parser                  = re.compile(r'group_rank=(?P<rank>\d+)')

layer_parser                        = re.compile(r'name: (?P<layerid>\d+).(?P<layername>.+), param.size: torch.Size\(\[(?P<sizeliststr>.+)\]\)')

json_dict = {}
layer_names = [[]] * 24
layer_sizes = [[]] * 24

def res_parser(file):
    print(f'processing: {file}')
    with open(file, 'r') as f:
        for line in f:
            if layer_parser.search(line):
                layerid = int(layer_parser.search(line).group('layerid'))
                if layerid >= len(layer_names):
                    return
                layername = layer_parser.search(line).group('layername')
                sizestrlist = layer_parser.search(line).group('sizeliststr').split(',')
                sizelist = []
                for sizestr in sizestrlist:
                    sizelist.append(int(sizestr))
                layer_names[layerid].append(layername)
                layer_sizes[layerid].append(sizelist)


for gpu in range(4):
    res_parser('res/others/90/nodes_8/node_' + str(gpu) + '.txt')

def generate_dict():
    json_dict['world_size'] = 16
    json_dict['layers'] = []
    for i in range(json_dict['world_size']):
        subdict = {}
        subdict['sizes'] = []
        subdict['names'] = []
        for j in range(24 // json_dict['world_size']):
            subdict['sizes'].extend(layer_sizes[i * j + j])
            subdict['names'].extend(layer_names[i * j + j])
        subdict['ranks'] = [i, 8 + i]
        json_dict['layers'].append(subdict)

def generate_json(file):
    generate_dict()
    with open(file, 'w') as fp:
        json.dump(json_dict, fp)

generate_json('tools/scalesimulator/' + 'res.json')