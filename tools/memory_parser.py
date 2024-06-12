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
from typing import NamedTuple
import random

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
cmd_parser                          = re.compile(r'Execute step (?P<cmdstep>\d+) Command (?P<cmd>\S+)\(buffer_id=(?P<bufferid>.+), stage_id=(?P<stageid>\d+)\)')

cmd_memory_parser                   = re.compile(r'cmd (?P<cmdname>\w+)\((.+)\) memory \(MB\) \| allocated: (?P<allocated>\d+\.\d+) \| max allocated: (?P<maxallocated>\d+\.\d+) \| reserved: (?P<reserved>\d+\.\d+) \| max reserved: (?P<maxreserved>\d+\.\d+)')
layer_memory_parser                 = re.compile(r'layer (?P<layernum>\d+) memory \(MB\) \| allocated: (?P<allocated>\d+\.\d+) \| max allocated: (?P<maxallocated>\d+\.\d+) \| reserved: (?P<reserved>\d+\.\d+) \| max reserved: (?P<maxreserved>\d+\.\d+)')

global_rank_parser                  = re.compile(r'group_rank=(?P<rank>\d+)')

get_colors = lambda n: dict(zip([i for i in range(n)], ["#%06x" % random.randint(0, 0xFFFFFF) for _ in range(n)]))

class CmdMemoryMetaData(NamedTuple):
    cmdname: str
    data: list

class LayerMemoryMetaData(NamedTuple):
    layernum: int
    data: list
    
all_cmds = {}

def res_parser(file):
    print(f'processing: {file}')
    cmdmemorydata = []
    layermemorydata, maxlayernum = [], 0
    with open(file, 'r') as f:
        for line in f:
            if is_log_parser.search(line):
                if start_schedule_parser.search(line):
                    cmdmemorydata.append([])
                    layermemorydata.append([])
            elif cmd_memory_parser.search(line):
                cmdname = cmd_memory_parser.search(line).group('cmdname')
                all_cmds[cmdname] = True
                allocated = cmd_memory_parser.search(line).group('allocated')
                maxallocated = cmd_memory_parser.search(line).group('maxallocated')
                reserved = cmd_memory_parser.search(line).group('reserved')
                maxreserved = cmd_memory_parser.search(line).group('maxreserved')
                cmdmemorydata[-1].append(CmdMemoryMetaData(cmdname, [allocated, maxallocated, reserved, maxreserved]))
            elif layer_memory_parser.search(line):
                layernum = layer_memory_parser.search(line).group('layernum')
                if int(layernum) > maxlayernum:
                    maxlayernum = int(layernum)
                allocated = layer_memory_parser.search(line).group('allocated')
                maxallocated = layer_memory_parser.search(line).group('maxallocated')
                reserved = layer_memory_parser.search(line).group('reserved')
                maxreserved = layer_memory_parser.search(line).group('maxreserved')
                layermemorydata[-1].append(LayerMemoryMetaData(layernum, [allocated, maxallocated, reserved, maxreserved]))
    return cmdmemorydata, layermemorydata, maxlayernum

def plot_one(file, memorydata, maxlayernum, iscmd):
    fig, axes = plt.subplots(2, 2)
    fig.set_size_inches(20, 20)
    sumx = 5 * len(memorydata)
    for i in range(len(memorydata)):
        sumx += len(memorydata[i])
    x = [xi for xi in range(sumx)]
    y = [[], [], [], []]
    colors = []
    color_map = {'RecvActivation': 'blue',
                 'SendActivation': 'cyan',
                 'ForwardPass': 'green',
                 'BackwardPass': 'lime',
                 'RecvGrad': 'pink',
                 'SendGrad': 'yellow',
                 'ReduceGrads': 'goldenrod',
                 'OptimizerStep': 'magenta',
                 'LoadMicroBatch': 'purple',
                 'layer': 'black'}
    if not iscmd:
        color_map = get_colors(maxlayernum + 1)
    for i in range(len(memorydata)):
        for j in range(5):
            for k in range(4):
                y[k].append(0)
            colors.append('white')
        for j in range(len(memorydata[i])):
            y[0].append(float(memorydata[i][j].data[0]))
            y[1].append(float(memorydata[i][j].data[1]))
            y[2].append(float(memorydata[i][j].data[2]))
            y[3].append(float(memorydata[i][j].data[3]))
            if iscmd:
                colors.append(color_map[memorydata[i][j].cmdname])
            else:
                colors.append(color_map[int(memorydata[i][j].layernum)])
    assert len(x) == len(y[0]) == len(y[1]) == len(y[2]) == len(y[3])
    axes[0, 0].bar(x, y[0], color=colors)
    axes[0, 1].bar(x, y[1], color=colors)
    axes[1, 0].bar(x, y[2], color=colors)
    axes[1, 1].bar(x, y[3], color=colors)
    plt.legend(handles=[mpatches.Patch(color=color, label=label) for label, color in color_map.items()], bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    if not os.path.exists('res/graph/memory/' + file.split('/')[-3] + '/'):
        os.makedirs('res/graph/memory/' + file.split('/')[-3] + '/')
    if not os.path.exists('res/graph/memory/' + file.split('/')[-3] + '/' + file.split('/')[-2]):
        os.makedirs('res/graph/memory/' + file.split('/')[-3] + '/' + file.split('/')[-2])
    if iscmd:
        plt.savefig('res/graph/memory/' + file.split('/')[-3] + '/' + file.split('/')[-2] + '/' + file.split('/')[-1].split('.')[0] + '_cmd.png')
    else:
        plt.savefig('res/graph/memory/' + file.split('/')[-3] + '/' + file.split('/')[-2] + '/' + file.split('/')[-1].split('.')[0] + '_layer.png')
    plt.close(fig)

def plot_memory(file):
    cmdmemorydata, layer_memorydata, maxlayernum = res_parser(file)
    plot_one(file, cmdmemorydata, maxlayernum, True)
    plot_one(file, layer_memorydata, maxlayernum, False)

files = []
for i in range(4):
    files.append('res/mem_trace/normal/nodes_8_90/node_' + str(i) + '.txt')
    files.append('res/mem_trace/normal/nodes_8_91/node_' + str(i) + '.txt')
    files.append('res/mem_trace/error/nodes_8_90/node_' + str(i) + '.txt')
    files.append('res/mem_trace/error/nodes_8_91/node_' + str(i) + '.txt')

for file in files:
    plot_memory(file)