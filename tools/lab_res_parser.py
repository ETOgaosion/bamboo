import argparse
import re
from dateutil import parser as dateparser
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Process the lab code output')
parser.add_argument('--num-nodes', required=True, action='store', type=int, help='the total number of nodes been executed')
args = parser.parse_args()

num_nodes = args.num_nodes
print(f'emphasizing {num_nodes} data')

# judge the log line
is_log_parser = re.compile(r'\[ \d{2,}\|\d{2,} \]')
# extract the time
time_parser = re.compile(r'(?P<time>\d{4,}-\d{2,}-\d{2,} \d{2,}:\d{2,}:\d{2,}.\d+)')
# extract the batch operation
start_batch_parser = re.compile(r'START BATCH (?P<batchid>\d+)')
finish_batch_parser = re.compile(r'FINISH BATCH (?P<batchid>\d+) took (?P<batchtime>\S+) s')
start_local_model_train_parser = re.compile(r'START LOCAL MODEL TRAIN (?P<globalstep>\d+)')
finish_local_model_train_parser = re.compile(r'FINISH LOCAL MODEL TRAIN (?P<globalstep>\d+)')
failure_node_detect_parser = re.compile(r'\[Engine\] Signal handler called with signal 15')
# extract the failure
failure_detect_parser = re.compile(r'FAILURES')
# extract the exception
start_next_stage_exception_parser = re.compile(r'START NextStageException fallback schedule (?P<globalstep>\d+)')
finish_next_stage_exception_parser = re.compile(r'FINISH NextStageException fallback schedule (?P<globalstep>\d+)')
start_prev_stage_exception_parser = re.compile(r'START PrevStageException fallback schedule (?P<globalstep>\d+)')
finish_prev_stage_exception_parser = re.compile(r'FINISH PrevStageException fallback schedule (?P<globalstep>\d+)')
# extract the reconfigure
start_reconfigure_parser = re.compile(r'START RECONFIGURE (?P<globalstep>\d+)')
finish_save_shadow_node_parser = re.compile(r'FINISH SAVE SHADOW NODE STATE (?P<globalstep>\d+)')
start_reconfigure_cluster_parser = re.compile(r'START RECONFIGURE CLUSTER and TRANSFER LAYERS (?P<globalstep>\d+)')
finish_reconfigure_parser = re.compile(r'FINISH RECONFIGURE (?P<globalstep>\d+)')

raw_data_tags = ['start_batch_times', 'finish_batch_times', 'start_local_model_train_times', 'finish_local_model_train_times', 'batch_times', 'start_next_stage_exception_times', 'finish_next_stage_exception_times', 'start_prev_stage_exception_times', 'finish_prev_stage_exception_times', 'start_reconfigure_times', 'finish_save_shadow_node_times', 'start_reconfigure_cluster_times', 'finish_reconfigure_times', 'fail_point']
mid_data_tags = ['delta_batch_times', 'delta_local_model_train_times', 'delta_next_stage_exception_times', 'delta_prev_stage_exception_times', 'delta_reconfigure_times', 'delta_reconfigure_cluster_times', 'delta_save_shadow_node_times', 'fail_point', 'maxi', 'mini']
tags = ['delta_batch_time', 'delta_local_model_train_time', 'delta_next_stage_exception_time', 'delta_prev_stage_exception_time', 'delta_reconfigure_time', 'delta_reconfigure_cluster_time', 'delta_save_shadow_node_time']

def res_parser(node):
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
    fail_point = -1
    with open('res/lab/node_' + str(node) + ".txt", 'r') as fp:
        for line in fp.readlines():
            if fail_point == -1 and (failure_node_detect_parser.match(line) or failure_detect_parser.search(line)):
                fail_point = len(raw_data['start_batch_times'])
            if is_log_parser.match(line) is None:
                continue
            time = time_parser.search(line)
            start_batch = start_batch_parser.search(line)
            if start_batch:
                batchid = int(start_batch.group('batchid'))
                if not raw_data['start_batch_times']:
                    if fail_point != -1:
                        fail_point += batchid
                raw_data['start_batch_times'][batchid] = dateparser.parse(time.group('time'))
                continue
            finish_batch = finish_batch_parser.search(line)
            if finish_batch:
                batchid = int(finish_batch.group('batchid'))
                raw_data['finish_batch_times'][batchid] = dateparser.parse(time.group('time'))
                raw_data['batch_times'][batchid] = float(finish_batch.group('batchtime'))
                continue
            start_local_model_train = start_local_model_train_parser.search(line)
            if start_local_model_train:
                globalstep = int(start_local_model_train.group('globalstep'))
                raw_data['start_local_model_train_times'][globalstep] = dateparser.parse(time.group('time'))
                continue
            finish_local_model_train = finish_local_model_train_parser.search(line)
            if finish_local_model_train:
                globalstep = int(finish_local_model_train.group('globalstep'))
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
    return raw_data, fail_point

def time2int(td):
    return td.total_seconds() * 1000

def handle_data(raw_data):
    mid_data = {
        'delta_batch_times': {},
        'delta_local_model_train_times': {},
        'delta_next_stage_exception_times': {},
        'delta_prev_stage_exception_times': {},
        'delta_reconfigure_times': {},
        'delta_reconfigure_cluster_times': {},
        'delta_save_shadow_node_times': {},
        'fail_point': fail_point
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
        mid_data['delta_reconfigure_times'][k] = time2int(raw_data['finish_reconfigure_times'][k] - v)
        mid_data['delta_reconfigure_cluster_times'][k] = time2int(raw_data['finish_reconfigure_times'][k] - raw_data['start_reconfigure_cluster_times'][k])
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
            data[k]['delta_reconfigure_time'] = mid_data['delta_reconfigure_times'][k] + data[k]['delta_prev_stage_exception_time']
            data[k]['delta_reconfigure_cluster_time'] = mid_data['delta_reconfigure_cluster_times'][k] + data[k]['delta_reconfigure_time']
            data[k]['delta_save_shadow_node_time'] = mid_data['delta_save_shadow_node_times'][k] + data[k]['delta_reconfigure_cluster_time']
    return data, max(mid_data['delta_batch_times'].values()), min(mid_data['delta_batch_times'].values())

def plot(node, data, maxi, mini, fail_point):
    c_success, c_fail = ['blue', 'cyan', 'goldenrod', 'orange', 'green', 'salmon', 'magenta'], []
    zorder, alpha = [], []
    for i in range(7):
        c_fail.append('dark' + c_success[i])
        zorder.append(i)
        alpha = 1.0 - i * 0.1
    for k, v in data.items():
        if k >= fail_point:
            for j in range(7):
                if tags[j] in v:
                    plt.bar(k, v[tags[j]], color=c_fail[j], zorder=zorder[j], alpha=alpha)
        else:
            for j in range(7):
                if tags[j] in v:
                    plt.bar(k, v[tags[j]], color=c_success[j], zorder=zorder[j], alpha=alpha)
    plt.title('Node ' + str(node) + ' Execution Time Statistics')
    plt.xlabel('Batch Number')
    plt.ylim(mini - 200, maxi + 200)
    plt.ylabel('Execution Time (ms)')
    plt.savefig('res/graph/node_' + str(node) + '.png')
    plt.close()

for i in range(0, num_nodes):
    raw_data, fail_point = res_parser(i)
    
    data, maxi, mini = handle_data(raw_data)
    
    plot(i, data, maxi, mini, fail_point)