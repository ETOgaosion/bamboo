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
finish_schedule_parser               = re.compile(r'FINISH FIRST TRY TO SCHEDULE (?P<globalstep>\d+)')
cmd_parser                          = re.compile(r'Execute step (?P<cmdstep>\d+) Command (?P<cmd>\S+)\(buffer_id=(?P<bufferid>.+), stage_id=(?P<stageid>\d+)\)')

global_rank_parser                  = re.compile(r'group_rank=(?P<rank>\d+)')

cmd_color_map = {'RecvActivation': 'blue', 'SendActivation': 'cyan', 'ForwardPass': 'green', 'BackwardPass': 'lime', 'RecvGrad': 'pink', 'SendGrad': 'yellow', 'ReduceGrads': 'goldenrod', 'OptimizerStep': 'magenta'}

global_ranks = {}
global_ranks_raw_filename = {}
total_time_list = {}
total_time = []
cmds_nums_list = {}
cmds_nums = []
steps_nums_list = {}
steps_nums = []

cache_cmds = {}
cache_time_data = {}

def time2int(td):
    return td / datetime.timedelta(microseconds=1)

def res_parser(file):
    print(f'processing: {file}')
    if file in cache_cmds:
        print("hit cache")
        return cache_cmds[file], cache_time_data[file]
    time_data = []
    cmds = []
    start_time = datetime.datetime.now()
    begin_time = datetime.datetime.now()
    start_calc = False
    with open(file, 'r') as f:
        nodes_num = int(file.split('/')[-2].split('_')[1])
        cmds_num = 0
        steps_num = 0
        for line in f:
            if global_rank_parser.search(line):
                filename = file.split('/')[-2] + '/' + file.split('/')[-3] + '/' + file.split('/')[-1]
                global_ranks_raw_filename[file] = global_rank_parser.search(line).group('rank')
                global_ranks[filename] = global_rank_parser.search(line).group('rank')
            if is_log_parser.search(line):
                if start_schedule_parser.search(line):
                    globalstep = start_schedule_parser.search(line).group('globalstep')
                    end_calc = (int(globalstep) > 1)
                    if end_calc:
                        break
                    start_calc = (globalstep == '1')
                    if not start_calc:
                        continue
                    start_time = dateparser.parse(time_parser.search(line).group('time'))
                    begin_time = start_time
                if start_calc == False:
                    continue
                if finish_schedule_parser.search(line):
                    if total_time_list.get(nodes_num) == None:
                        total_time_list[nodes_num] = []
                    else:
                        total_time_list[nodes_num].append(time2int(dateparser.parse(time_parser.search(line).group('time')) - begin_time))
                    if cmds_nums_list.get(nodes_num) == None:
                        cmds_nums_list[nodes_num] = []
                    else:
                        cmds_nums_list[nodes_num].append(cmds_num)
                    if steps_nums_list.get(nodes_num) == None:
                        steps_nums_list[nodes_num] = []
                    else:
                        steps_nums_list[nodes_num].append(steps_num)
                    time_data.append(time2int(dateparser.parse(time_parser.search(line).group('time')) - start_time))
                    time_data = time_data[1:]
                    break
                if cmd_parser.search(line):
                    steps_num = int(cmd_parser.search(line).group('cmdstep')) + 1
                    cmds_num += 1
                    cmd = cmd_parser.search(line).group('cmd')
                    cmds.append(cmd)
                    time_data.append(time2int(dateparser.parse(time_parser.search(line).group('time')) - start_time))
                    start_time = dateparser.parse(time_parser.search(line).group('time'))
    cache_cmds[file] = cmds
    cache_time_data[file] = time_data
    return cmds, time_data

def plot(file, targetdir=""):
    cmds, time_data = res_parser(file)
    fig, ax = plt.subplots()
    fig.set_size_inches(15, 10)
    for i, cmd in enumerate(cmds):
        ax.bar(i, time_data[i], color=cmd_color_map[cmd])
    ax.set(xlabel='cmd', ylabel='times', title='cmd')
    ax.set_ylim(0, 1200000)
    plt.legend(handles=[mpatches.Patch(color=color, label=label) for label, color in cmd_color_map.items()], bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    plt.savefig('res/graph/' + targetdir + "/" + file.split('/')[-2] + '_' + file.split('/')[-1].split('.')[0] + '.png')
    plt.close(fig)

plot('res/others/90/nodes_8/node_0.txt')
plot('res/others/90/nodes_8/node_1.txt')
plot('res/others/91/nodes_8/node_0.txt')
plot('res/others/91/nodes_8/node_1.txt')
plot('res/others/92/nodes_8/node_0.txt')
plot('res/others/92/nodes_8/node_1.txt')
plot('res/others/46/nodes_8/node_0.txt')
plot('res/others/46/nodes_8/node_1.txt')

for i in range(4):
    plot('res/others/90/nodes_8/node_' + str(i) + '.txt', '90')
    plot('res/others/90/nodes_9/node_' + str(i) + '.txt', '90')
    plot('res/others/90/nodes_10/node_' + str(i) + '.txt', '90')
    plot('res/others/90/nodes_11/node_' + str(i) + '.txt', '90')
    plot('res/others/90/nodes_12/node_' + str(i) + '.txt', '90')
    plot('res/others/90/nodes_14/node_' + str(i) + '.txt', '90')
    plot('res/others/90/nodes_15/node_' + str(i) + '.txt', '90')
    plot('res/others/90/nodes_16/node_' + str(i) + '.txt', '90')

for i in range(4):
    plot('res/others/91/nodes_8/node_' + str(i) + '.txt', '91')
    plot('res/others/91/nodes_9/node_' + str(i) + '.txt', '91')
    plot('res/others/91/nodes_10/node_' + str(i) + '.txt', '91')
    plot('res/others/91/nodes_11/node_' + str(i) + '.txt', '91')
    plot('res/others/91/nodes_12/node_' + str(i) + '.txt', '91')
    plot('res/others/91/nodes_14/node_' + str(i) + '.txt', '91')
    plot('res/others/91/nodes_15/node_' + str(i) + '.txt', '91')
    plot('res/others/91/nodes_16/node_' + str(i) + '.txt', '91')

plot('res/others/92/nodes_9/node_0.txt', '92')
for i in range(2):
    plot('res/others/92/nodes_10/node_' + str(i) + '.txt', '92')
for i in range(3):
    plot('res/others/92/nodes_11/node_' + str(i) + '.txt', '92')
for i in range(4):
    plot('res/others/92/nodes_12/node_' + str(i) + '.txt', '92')
    plot('res/others/92/nodes_14/node_' + str(i) + '.txt', '92')
    plot('res/others/92/nodes_15/node_' + str(i) + '.txt', '92')
    plot('res/others/92/nodes_16/node_' + str(i) + '.txt', '92')

for i in range(2):
    plot('res/others/46/nodes_14/node_' + str(i) + '.txt', '46')
for i in range(3):
    plot('res/others/46/nodes_15/node_' + str(i) + '.txt', '46')
for i in range(4):
    plot('res/others/46/nodes_16/node_' + str(i) + '.txt', '46')

def nodes8_plot(axes, files):
    for file in files:
        cmds, time_data = res_parser(file)
        index = int(global_ranks_raw_filename[file])
        axes[index].set_title(file)
        for i, cmd in enumerate(cmds):
            axes[index].bar(i, time_data[i], color=cmd_color_map[cmd])
        axes[index].set_ylim(0, 300000)

files = []
files_mixed = []
fig, axes = plt.subplots(2, 8)
fig.set_size_inches(80, 20)
for i in range(4):
    files.append('res/others/90/nodes_8/node_' + str(i) + '.txt')
    files.append('res/others/91/nodes_8/node_' + str(i) + '.txt')
for i in range(2):
    files_mixed.append('res/others/90/nodes_8_mixed/node_' + str(i) + '.txt')
    files_mixed.append('res/others/91/nodes_8_mixed/node_' + str(i) + '.txt')
    files_mixed.append('res/others/92/nodes_8_mixed/node_' + str(i) + '.txt')
    files_mixed.append('res/others/46/nodes_8_mixed/node_' + str(i) + '.txt')
nodes8_plot(axes[0], files)
nodes8_plot(axes[1], files_mixed)
plt.legend(handles=[mpatches.Patch(color=color, label=label) for label, color in cmd_color_map.items()], bbox_to_anchor=(1, 0.5))
plt.tight_layout()
plt.savefig('res/graph/node_8_cmp.png')

global_ranks = dict(sorted(global_ranks.items(), key=lambda x: (int(x[0].split('/')[0].split('_')[1]), len(x[0].split('/')[0]), int(x[0].split('/')[1]), x[0].split('/')[2])))
pprint.pp(global_ranks)

node_ranks = {}
for k, v in global_ranks.items():
    v = int(v)
    nodes_num_key = int(k.split('/')[0].split('_')[1])
    node_key = int(k.split('/')[1])
    gpu_key = int(k.split('/')[2].split('_')[1][0])
    if node_ranks.get(nodes_num_key) == None:
        node_ranks[nodes_num_key] = {}
    if node_ranks[nodes_num_key].get(node_key) == None:
        node_ranks[nodes_num_key][node_key] = {v: True}
    else:
        node_ranks[nodes_num_key][node_key][v] = True
connected_num = []
for k, v in node_ranks.items():
    connected_num.append(0)
    for node_k, node_v in v.items():
        for rank_k, rank_v in node_v.items():
            get_k = (rank_k + 1) % k
            if node_v.get(get_k) != None:
                connected_num[-1] += 1
connected_percentage = []
for i in range(len(connected_num)):
    connected_percentage.append(connected_num[i] / (i + 8))
    if (i + 8) == 12:
        connected_percentage.append(0)

def plot_connected_percentage(connected_percentage):
    fig, ax = plt.subplots()
    fig.set_size_inches(15, 10)
    bar_container = ax.bar(range(8, 17), connected_percentage)
    ax.set(xlabel='nodes', ylabel='times', title='connected_num')
    ax.bar_label(bar_container)
    plt.tight_layout()
    plt.savefig('res/graph/connected_percentage.png')
    plt.close(fig)


plot_connected_percentage(connected_percentage)

def plot_total_time():
    fig, ax = plt.subplots()
    fig.set_size_inches(15, 10)
    for i in range(8, 17):
        if i == 13:
            total_time.append(0)
            continue
        total_time.append(statistics.mean(total_time_list[i]))
    bar_container = ax.bar(range(8, 17), total_time)
    ax.set(xlabel='nodes', ylabel='times', title='total time')
    ax.bar_label(bar_container)
    plt.tight_layout()
    plt.savefig('res/graph/total_time.png')
    plt.close(fig)

plot_total_time()

def plot_cmds_nums():
    fig, ax = plt.subplots()
    fig.set_size_inches(15, 10)
    for i in range(8, 17):
        if i == 13:
            cmds_nums.append(0)
            continue
        cmds_nums.append(statistics.mean(cmds_nums_list[i]))
    bar_container = ax.bar(range(8, 17), cmds_nums)
    ax.set(xlabel='nodes', ylabel='cmds', title='cmds nums')
    ax.bar_label(bar_container)
    plt.tight_layout()
    plt.savefig('res/graph/cmds_nums.png')
    plt.close(fig)

plot_cmds_nums()

def plot_steps_nums():
    fig, ax = plt.subplots()
    fig.set_size_inches(15, 10)
    for i in range(8, 17):
        if i == 13:
            steps_nums.append(0)
            continue
        steps_nums.append(statistics.mean(steps_nums_list[i]))
    bar_container = ax.bar(range(8, 17), steps_nums)
    ax.set(xlabel='nodes', ylabel='steps', title='steps nums')
    ax.bar_label(bar_container)
    plt.tight_layout()
    plt.savefig('res/graph/steps_nums.png')
    plt.close(fig)

plot_steps_nums()

reverse_global_rank = {}
for k, v in global_ranks_raw_filename.items():
    if reverse_global_rank.get(v) == None:
        reverse_global_rank[v] = [k]
    else:
        reverse_global_rank[v].append(k)

def multiplot(files, nodes):
    fig, axes = plt.subplots(1, len(files))
    fig.set_size_inches(10 * (len(files)), 10)
    for index, file in enumerate(files):
        axes[index].set_title(file)
        cmds, time_data = res_parser(file)
        for i, cmd in enumerate(cmds):
            axes[index].bar(i, time_data[i], color=cmd_color_map[cmd])
        axes[index].set_ylim(0, 1200000)
    plt.legend(handles=[mpatches.Patch(color=color, label=label) for label, color in cmd_color_map.items()], bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    plt.savefig('res/graph/node_' + str(nodes) + '.png')

for i in range(8):
    reverse_global_rank[str(i)] = sorted(reverse_global_rank[str(i)], key=lambda x: int(x.split('/')[-2].split('_')[1]))

print(reverse_global_rank)

for i in range(8):
    multiplot(reverse_global_rank[str(i)], i)

def allplot(axes, files, cmd_color_map):
    for index, file in enumerate(files):
        axes[index].set_title(file)
        cmds, time_data = res_parser(file)
        for i, cmd in enumerate(cmds):
            axes[index].bar(i, time_data[i], color=cmd_color_map[cmd])
        axes[index].set_ylim(0, 1200000)

for i in range(8):
    reverse_global_rank[str(i)] = sorted(reverse_global_rank[str(i)], key=lambda x: int(x.split('/')[-2].split('_')[1]))

print(reverse_global_rank)

fig, axes = plt.subplots(8, len(reverse_global_rank['0']))
fig.set_size_inches(10 * 8, 10 * len(reverse_global_rank['0']))
for i in range(8):
    allplot(axes[i], reverse_global_rank[str(i)], cmd_color_map)
plt.legend(handles=[mpatches.Patch(color=color, label=label) for label, color in cmd_color_map.items()], bbox_to_anchor=(1, 0.5))
plt.tight_layout()
plt.savefig('res/graph/all_nodes.png')

def allbreifplot(axes, files, cmd_color_map, node_idx):
    axes.set_title('node_' + str(node_idx))
    for index, file in enumerate(files):
        cmds, time_data = res_parser(file)
        new_cmds_dict, new_cmds, new_time_data_list, new_time_data = {}, cmd_color_map.keys(), [], []
        for i, cmd in enumerate(new_cmds):
            new_cmds_dict[cmd] = i
            new_time_data_list.append([])
        for i, cmd in enumerate(cmds):
            new_time_data_list[new_cmds_dict[cmd]].append(time_data[i])
        for i in range(len(new_cmds)):
            if len(new_time_data_list[i]) == 0:
                new_time_data.append(0)
            else:
                new_time_data.append(statistics.mean(new_time_data_list[i]))
        for i, cmd in enumerate(new_cmds):
            axes.bar(i * (len(files) + 1) + index, new_time_data[i], color=cmd_color_map[cmd])

for i in range(8):
    reverse_global_rank[str(i)] = sorted(reverse_global_rank[str(i)], key=lambda x: int(x.split('/')[-2].split('_')[1]))

print(reverse_global_rank)

fig, axes = plt.subplots(8)
fig.set_size_inches(10 * (len(reverse_global_rank[str(i)]) + 1), 10 * 8)
for i in range(8):
    allbreifplot(axes[i], reverse_global_rank[str(i)], cmd_color_map, i)
plt.legend(handles=[mpatches.Patch(color=color, label=label) for label, color in cmd_color_map.items()], bbox_to_anchor=(1, 0.5))
plt.tight_layout()
plt.savefig('res/graph/all_nodes_breif.png')