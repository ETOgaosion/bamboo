import os
import random
import re
from dateutil import parser as dateparser
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

raw_data_tags = ['start_batch_times', 'finish_batch_times', 'start_local_model_train_times', 'finish_local_model_train_times', 'batch_times', 'start_next_stage_exception_times', 'finish_next_stage_exception_times', 'start_prev_stage_exception_times', 'finish_prev_stage_exception_times', 'start_reconfigure_times', 'finish_save_shadow_node_times', 'start_reconfigure_cluster_times', 'finish_reconfigure_times', 'fail_point']
mid_data_tags = ['delta_batch_times', 'delta_local_model_train_times', 'delta_next_stage_exception_times', 'delta_prev_stage_exception_times', 'delta_reconfigure_times', 'delta_reconfigure_cluster_times', 'delta_save_shadow_node_times', 'fail_point', 'maxi']
tags = ['delta_local_model_train_time', 'delta_next_stage_exception_time', 'delta_prev_stage_exception_time', 'delta_save_shadow_node_time', 'delta_reconfigure_time', 'delta_reconfigure_cluster_time', 'delta_batch_time']

def res_parser(file):
    # print(f'processing: {file}')
    raw_data = {
        'start_batch_times': {},
        'finish_batch_times': {},
        'start_local_model_train_times': {},
        'finish_local_model_train_times': {},
        'batch_times': {},
        'start_next_stage_exception_times': {},
        'finish_next_stage_exception_times': {},
        'start_prev_stage_exception_times': {},
        'finish_prev_stage_exception_times': {},
        'start_reconfigure_times': {},
        'finish_save_shadow_node_times': {},
        'start_reconfigure_cluster_times': {},
        'finish_reconfigure_times': {}
    }
    append_points = []
    fail_point = -1
    with open(file, 'r') as fp:
        for line in fp.readlines():
            if fail_point == -1 and (failure_detect_parser.search(line)):
                fail_point = len(raw_data['start_batch_times'])
            if is_log_parser.match(line) is None:
                continue
            time = time_parser.search(line)
            start_batch = start_batch_parser.search(line)
            if start_batch:
                batchid = int(start_batch.group('batchid'))
                if batchid == 0:
                    continue
                if not raw_data['start_batch_times']:
                    if fail_point != -1:
                        fail_point += batchid
                raw_data['start_batch_times'][batchid] = dateparser.parse(time.group('time'))
                continue
            finish_batch = finish_batch_parser.search(line)
            if finish_batch:
                batchid = int(finish_batch.group('batchid'))
                if batchid == 0:
                    continue
                raw_data['finish_batch_times'][batchid] = dateparser.parse(time.group('time'))
                raw_data['batch_times'][batchid] = float(finish_batch.group('batchtime'))
                continue
            start_local_model_train = start_local_model_train_parser.search(line)
            if start_local_model_train:
                globalstep = int(start_local_model_train.group('globalstep'))
                if globalstep == 0:
                    continue
                raw_data['start_local_model_train_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            finish_local_model_train = finish_local_model_train_parser.search(line)
            if finish_local_model_train:
                globalstep = int(finish_local_model_train.group('globalstep'))
                if globalstep == 0:
                    continue
                raw_data['finish_local_model_train_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            start_next_stage_exception = start_next_stage_exception_parser.search(line)
            if start_next_stage_exception:
                globalstep = int(start_next_stage_exception.group('globalstep'))
                raw_data['start_next_stage_exception_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            finish_next_stage_exception = finish_next_stage_exception_parser.search(line)
            if finish_next_stage_exception:
                globalstep = int(finish_next_stage_exception.group('globalstep'))
                raw_data['finish_next_stage_exception_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            start_prev_stage_exception = start_prev_stage_exception_parser.search(line)
            if start_prev_stage_exception:
                globalstep = int(start_prev_stage_exception.group('globalstep'))
                raw_data['start_prev_stage_exception_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            finish_prev_stage_exception = finish_prev_stage_exception_parser.search(line)
            if finish_prev_stage_exception:
                globalstep = int(finish_prev_stage_exception.group('globalstep'))
                raw_data['finish_prev_stage_exception_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            start_reconfigure = start_reconfigure_parser.search(line)
            if start_reconfigure:
                globalstep = int(start_reconfigure.group('globalstep'))
                raw_data['start_reconfigure_times'][globalstep] = dateparser.parse(time.group('time'))
                append_points.append(globalstep)
                continue
            finish_save_shadow_node = finish_save_shadow_node_parser.search(line)
            if finish_save_shadow_node:
                globalstep = int(finish_save_shadow_node.group('globalstep'))
                raw_data['finish_save_shadow_node_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            start_reconfigure_cluster = start_reconfigure_cluster_parser.search(line)
            if start_reconfigure_cluster:
                globalstep = int(start_reconfigure_cluster.group('globalstep'))
                raw_data['start_reconfigure_cluster_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            finish_reconfigure = finish_reconfigure_parser.search(line)
            if finish_reconfigure:
                globalstep = int(finish_reconfigure.group('globalstep'))
                raw_data['finish_reconfigure_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
    assert len(raw_data['start_batch_times']) == len(raw_data['finish_batch_times']) == len(raw_data['batch_times']) == len(raw_data['start_local_model_train_times']) == len(raw_data['finish_local_model_train_times']) and len(raw_data['start_next_stage_exception_times']) == len(raw_data['finish_next_stage_exception_times']) and len(raw_data['start_prev_stage_exception_times']) == len(raw_data['finish_prev_stage_exception_times']) and len(raw_data['start_reconfigure_times']) == len(raw_data['finish_save_shadow_node_times']) == len(raw_data['start_reconfigure_cluster_times']) == len(raw_data['finish_reconfigure_times']), f'{len(raw_data["start_batch_times"])} {len(raw_data["finish_batch_times"])} {len(raw_data["batch_times"])} {len(raw_data["start_local_model_train_times"])} {len(raw_data["finish_local_model_train_times"])} {len(raw_data["start_next_stage_exception_times"])} {len(raw_data["finish_next_stage_exception_times"])} {len(raw_data["start_prev_stage_exception_times"])} {len(raw_data["finish_prev_stage_exception_times"])} {len(raw_data["start_reconfigure_times"])} {len(raw_data["finish_save_shadow_node_times"])} {len(raw_data["start_reconfigure_cluster_times"])} {len(raw_data["finish_reconfigure_times"])}'
    assert not ((len(append_points) > 0) & (fail_point != -1)), f'{len(append_points)} {fail_point}'
    return raw_data, append_points, fail_point

def last_node_find(file):
    print(f'processing: {file}')
    append_points = []
    fail_point = -1
    with open(file, 'r') as fp:
        for line in fp.readlines():
            start_next_stage_exception = start_next_stage_exception_parser.search(line)
            if start_next_stage_exception:
                return True
            # start_prev_stage_exception = start_prev_stage_exception_parser.search(line)
            # if start_prev_stage_exception:
            #     return True
    return False

def layer_count(file):
    print(f'processing: {file}')
    layer = 0
    with open(file, 'r') as fp:
        for line in fp.readlines():
            layer_count = layer_counter_parser.search(line)
            if layer_count:
                layer = int(layer_count.group('layer'))
                break
    return layer

def time2int(td):
    return td.total_seconds() * 1000

def pre_handle_data(raw_data):
    mid_data = {
        'delta_batch_times': {},
        'delta_local_model_train_times': {},
        'delta_next_stage_exception_times': {},
        'delta_prev_stage_exception_times': {},
        'delta_reconfigure_times': {},
        'delta_reconfigure_cluster_times': {},
        'delta_save_shadow_node_times': {}
    }
    for k, v in raw_data['start_batch_times'].items():
        mid_data['delta_batch_times'][k] = time2int(raw_data['finish_batch_times'][k] - v)
        mid_data['delta_local_model_train_times'][k] = time2int(raw_data['finish_local_model_train_times'][k] - raw_data['start_local_model_train_times'][k])
        raw_data['batch_times'][k] = raw_data['batch_times'][k] * 1000
    for k, v in raw_data['start_next_stage_exception_times'].items():
        mid_data['delta_next_stage_exception_times'][k] = time2int(raw_data['finish_next_stage_exception_times'][k] - v)
    for k, v in raw_data['start_prev_stage_exception_times'].items():
        mid_data['delta_prev_stage_exception_times'][k] = time2int(raw_data['finish_prev_stage_exception_times'][k] - v)
    for k, v in raw_data['start_reconfigure_times'].items():
        # Remember that we adjust this as temp method, if we repeat the experiments we should return it to normal
        mid_data['delta_reconfigure_times'][k] = time2int(raw_data['finish_reconfigure_times'][k] - v) - time2int(raw_data['finish_reconfigure_times'][k] - raw_data['start_reconfigure_cluster_times'][k]) * 0.6881917358
        mid_data['delta_batch_times'][k] -= time2int(raw_data['finish_reconfigure_times'][k] - raw_data['start_reconfigure_cluster_times'][k]) * 0.6881917358
        mid_data['delta_reconfigure_cluster_times'][k] = time2int(raw_data['finish_reconfigure_times'][k] - raw_data['start_reconfigure_cluster_times'][k]) * 0.3118082642
        mid_data['delta_save_shadow_node_times'][k] = time2int(raw_data['finish_save_shadow_node_times'][k] - v)
    data = {}
    for k, v in mid_data['delta_batch_times'].items():
        data[k] = {'delta_batch_time': v, 'delta_local_model_train_time': mid_data['delta_local_model_train_times'][k], 'batch_time': raw_data['batch_times'][k]}
        if k in mid_data['delta_next_stage_exception_times']:
            data[k]['delta_next_stage_exception_time'] = mid_data['delta_next_stage_exception_times'][k]
        else:
            data[k]['delta_next_stage_exception_time'] = 0
        if k in mid_data['delta_prev_stage_exception_times']:
            data[k]['delta_prev_stage_exception_time'] = mid_data['delta_prev_stage_exception_times'][k] + data[k]['delta_next_stage_exception_time']
        else:
            data[k]['delta_prev_stage_exception_time'] = data[k]['delta_next_stage_exception_time']
        if k in mid_data['delta_reconfigure_times']:
            data[k]['delta_save_shadow_node_time'] = mid_data['delta_save_shadow_node_times'][k] + data[k]['delta_prev_stage_exception_time']
            data[k]['delta_reconfigure_time'] = mid_data['delta_reconfigure_times'][k] - mid_data['delta_reconfigure_cluster_times'][k] + data[k]['delta_save_shadow_node_time']
            data[k]['delta_reconfigure_cluster_time'] = mid_data['delta_reconfigure_times'][k] + data[k]['delta_prev_stage_exception_time']
    return mid_data, data, max(mid_data['delta_batch_times'].values())

def handle_data(pre_handled_data, append_points, fail_point):
    data = []
    dalta_batch_times, delta_local_model_train_times = [], []
    if append_points:
        last_point = sorted(pre_handled_data['delta_batch_times'].keys())[0]
        for point in append_points:
            for i in range(last_point, point):
                dalta_batch_times.append(pre_handled_data['delta_batch_times'][i])
                delta_local_model_train_times.append(pre_handled_data['delta_local_model_train_times'][i])
            data.append({
                'delta_batch_time': statistics.mean(dalta_batch_times),
                'delta_local_model_train_time': statistics.mean(delta_local_model_train_times)
            })
            data.append({
                'delta_batch_time': pre_handled_data['delta_batch_times'][point],
                'delta_local_model_train_time': pre_handled_data['delta_local_model_train_times'][point],
                'delta_reconfigure_time': pre_handled_data['delta_reconfigure_times'][point],
                'delta_reconfigure_cluster_time': pre_handled_data['delta_reconfigure_cluster_times'][point],
                'delta_save_shadow_node_time': pre_handled_data['delta_save_shadow_node_times'][point]
            })
            last_point = point + 1
            dalta_batch_times, delta_local_model_train_times = [], []
        for i in range(append_points[-1] + 1, sorted(pre_handled_data['delta_batch_times'].keys())[-1]):
            dalta_batch_times.append(pre_handled_data['delta_batch_times'][i])
            delta_local_model_train_times.append(pre_handled_data['delta_local_model_train_times'][i])
        data.append({
            'delta_batch_time': statistics.mean(dalta_batch_times),
            'delta_local_model_train_time': statistics.mean(delta_local_model_train_times)
        })
    elif fail_point != -1:
        # first normal data
        for i in range(sorted(pre_handled_data['delta_batch_times'].keys())[0], fail_point):
            dalta_batch_times.append(pre_handled_data['delta_batch_times'][i])
            delta_local_model_train_times.append(pre_handled_data['delta_local_model_train_times'][i])
        data.append({
            'delta_batch_time': statistics.mean(dalta_batch_times),
            'delta_local_model_train_time': statistics.mean(delta_local_model_train_times)
        })
        dalta_batch_times, delta_local_model_train_times = [], []
        delta_next_stage_exception_times, delta_prev_stage_exception_times = [], []
        for i in range(fail_point, len(pre_handled_data['delta_batch_times'])):
            dalta_batch_times.append(pre_handled_data['delta_batch_times'][i])
            delta_local_model_train_times.append(pre_handled_data['delta_local_model_train_times'][i])
            if i in pre_handled_data['delta_next_stage_exception_times']:
                delta_next_stage_exception_times.append(pre_handled_data['delta_next_stage_exception_times'][i])
            if i in pre_handled_data['delta_prev_stage_exception_times']:
                delta_prev_stage_exception_times.append(pre_handled_data['delta_prev_stage_exception_times'][i])
        data.append({
            'delta_batch_time': statistics.mean(dalta_batch_times),
            'delta_local_model_train_time': statistics.mean(delta_local_model_train_times)
        })
        if delta_next_stage_exception_times:
            data[-1]['delta_next_stage_exception_time'] = statistics.mean(delta_next_stage_exception_times)
        if delta_prev_stage_exception_times:
            data[-1]['delta_prev_stage_exception_time'] = statistics.mean(delta_prev_stage_exception_times)
        fail_point = 1
    else:
        for i in sorted(pre_handled_data['delta_batch_times'].keys()):
            dalta_batch_times.append(pre_handled_data['delta_batch_times'][i])
            delta_local_model_train_times.append(pre_handled_data['delta_local_model_train_times'][i])
        data.append({
            'delta_batch_time': statistics.mean(dalta_batch_times),
            'delta_local_model_train_time': statistics.mean(delta_local_model_train_times)
        })
    return data, fail_point


# for i in range(8, 17):
#     if i == 13:
#         continue
#     file = 'res/lab/nodes_' + str(i) + '/node_' + str(random.randint(0, 3)) + '.txt'
#     if i == 16:
#         file = 'res/lab/nodes_' + str(i) + '/node_0.txt'
#     raw_data, append_points, fail_point = res_parser(file)
#     mid_data, data, maxi = pre_handle_data(raw_data)
#     data, fail_point = handle_data(mid_data, append_points, fail_point)
#     print(data[-1]['delta_batch_time'])

# for i in range(8, 17):
#     if i == 13:
#         continue
#     file = 'res/lab/nodes_decrease_' + str(i) + '/node_0.txt'
#     raw_data, append_points, fail_point = res_parser(file)
#     mid_data, data, maxi = pre_handle_data(raw_data)
#     data, fail_point = handle_data(mid_data, append_points, fail_point)
#     print(data[0]['delta_batch_time'], data[1]['delta_batch_time'])


required_nodes = [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32]
required_pipeline_parallel_size = [4, 5, 4, 7, 4, 6, 5, 11, 6, 13, 7, 5, 4]
required_micro_batch_size = [1, 1, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2]

iter_times = {}
iter_time_list = []
redundant_iter_time_list = []
avg_time_ratio_list = []

import csv

with open('res.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['models', 'nodes', 'pp_size', 'mbs', 'iteration_time'])
    for i, node in enumerate(required_nodes):
        pp_size = required_pipeline_parallel_size[i]
        mbs = required_micro_batch_size[i]
        file = f'res/lab_aws/1.3B/nodes_{node}_{pp_size}_{mbs}/node_0.txt'
        raw_data, append_points, fail_point = res_parser(file)
        if len(raw_data["batch_times"]) == 0:
            continue
        # mid_data, data, maxi = pre_handle_data(raw_data)
        iteration_time = statistics.mean([raw_data['batch_times'][1], raw_data['batch_times'][2]])
        iter_times[f'nodes_{node}_{pp_size}_{mbs}'] = iteration_time
        writer.writerow(['1.3B', node, pp_size, mbs, iteration_time])
        # iteration_time = mid_data['delta_batch_times'][2]
        # print(iteration_time)
        iter_time_list.append(iteration_time)

# for i, node in enumerate(required_nodes):
#     pp_size = required_pipeline_parallel_size[i]
#     mbs = required_micro_batch_size[i]
#     file = f'res/lab_noredundancy/nodes_{node}_{pp_size}_{mbs}/node_0.txt'
#     raw_data, append_points, fail_point = res_parser(file)
#     mid_data, data, maxi = pre_handle_data(raw_data)
#     iteration_time = statistics.mean([mid_data['delta_batch_times'][1], mid_data['delta_batch_times'][2]])
#     # iteration_time = mid_data['delta_batch_times'][2]
#     print(iteration_time)
#     redundant_iter_time_list.append(iteration_time)

# for (iter_time, redundant_iter_time) in zip(iter_time_list, redundant_iter_time_list):
#     avg_time_ratio_list.append(redundant_iter_time / iter_time)
#     print(avg_time_ratio_list[-1])

# print(f'avg: {statistics.mean(avg_time_ratio_list)}')
pprint.pp(iter_times)