import argparse
import re
from dateutil import parser as dateparser
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Process the lab code output')
parser.add_argument('--num-nodes', required=True, action='store', type=int, help='the total number of nodes been executed')
args = parser.parse_args()

num_nodes = args.num_nodes
print(f'emphasizing {num_nodes} data')

is_log_parser = re.compile(r'\[ \d{2,}\|\d{2,} \]')
time_parser = re.compile(r'(?P<time>\d{4,}-\d{2,}-\d{2,} \d{2,}:\d{2,}:\d{2,}.\d+)')
start_batch_parser = re.compile(r'STARTING BATCH (?P<batchid>\d+)')
finish_batch_parser = re.compile(r'FINISHING BATCH (?P<batchid>\d+) took (?P<batchtime>\S+) s')
failure_node_detect_parser = re.compile(r'\[Engine\] Signal handler called with signal 15')
failure_detect_parser = re.compile(r'FAILURES')

def res_parser(node):
    start_times, finish_times, batch_times, fail_list = [], [], [], []
    with open('res/lab/node_' + str(node) + ".txt", 'r') as fp:
        for line in fp.readlines():
            if failure_node_detect_parser.match(line) or failure_detect_parser.search(line):
                fail_list.append(True)
            if is_log_parser.match(line) is None:
                continue
            time = time_parser.search(line)
            start_batch = start_batch_parser.search(line)
            if start_batch:
                assert int(start_batch.group('batchid')) == len(start_times), f'{int(start_batch.group("batchid"))} != {len(start_times)}'
                start_times.append(dateparser.parse(time.group('time')))
            finish_batch = finish_batch_parser.search(line)
            if finish_batch:
                assert int(finish_batch.group('batchid')) == len(finish_times), f'{int(finish_batch.group("batchid"))} != {len(finish_times)}'
                finish_times.append(dateparser.parse(time.group('time')))
                batch_times.append(float(finish_batch.group('batchtime')))
                if len(finish_times) == len(fail_list) + 1:
                    fail_list.append(False)
    return start_times, finish_times, batch_times, fail_list

def time2int(td):
    return td.total_seconds() * 1000

def plot(node, start_times, finish_times, batch_time, fail_list):
    mini, maxi = 0, 0
    for i in range(1, len(start_times)):
        deltatime = time2int(finish_times[i] - start_times[i])
        batchtime = batch_time[i] * 1000
        if mini == 0:
            mini = deltatime
        elif mini > deltatime:
            mini = deltatime
        elif mini > batchtime:
            mini = batchtime
        if maxi < deltatime:
            maxi = deltatime
        elif maxi < batchtime:
            maxi = batchtime
        if fail_list[i]:
            plt.scatter([i, i], [deltatime, batchtime], c=['r', 'g'], s=[2, 2])
        else:
            plt.scatter([i, i], [deltatime, batchtime], c=['b', 'g'], s=[2, 2])
    plt.title('Node ' + str(node) + ' Execution Time Statistics')
    plt.xlabel('Batch Number')
    plt.ylim(mini - 200, maxi + 200)
    plt.ylabel('Execution Time (ms)')
    plt.savefig('res/graph/node_' + str(node) + '.png')
    plt.close()

for i in range(0, num_nodes):
    start_times, finish_times, batch_time, fail_list = res_parser(i)
    plot(i, start_times, finish_times, batch_time, fail_list)