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
import csv

def read_trace(file):
    if file.endswith(".csv"):
        seconds, operations, nodes = [], [], []
        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                seconds.append(row[0])
                operations.append(row[1])
                nodes.append(row[2])
        return seconds, operations, nodes

def reconfigure_case(file):
    print(file)
    seconds, operations, nodes = read_trace(file)
    aggregate = []
    last_second = seconds[0]
    num_nodes = 0
    for i in range(len(seconds)):
        if seconds[i] == last_second:
            num_nodes += 1
        else:
            aggregate.append([last_second, operations[i - 1], num_nodes])
            num_nodes = 1
            last_second = seconds[i]
    # pprint.pp(aggregate)
    cases = []
    diff_cases = {}
    num_nodes = aggregate[0][2]
    for i in range(1, len(aggregate)):
        before = num_nodes
        if aggregate[i][1] == 'add':
            num_nodes += aggregate[i][2]
        else:
            num_nodes -= aggregate[i][2]
        cases.append({'second': aggregate[i][0], 'before': before, 'after': num_nodes})
        diff_cases['before:' + str(before) + ' -> after:' + str(num_nodes)] = True
        # print(cases[-1])
    pprint.pp(list(diff_cases.keys()))
    return cases

# reconfigure_case('simulator/traces/g4dn-trace-16.csv')
# reconfigure_case('simulator/traces/g4dn-trace.csv')
# reconfigure_case('simulator/traces/p3-trace-16.csv')
# reconfigure_case('simulator/traces/p3-trace.csv')

def modify_trace(seconds, operations, nodes):
    trace = []
    current_node_num = 0
    included_nodes = {}
    for i in range(len(seconds)):
        if operations[i] == 'add' and current_node_num < 24:
            trace.append([seconds[i], operations[i], nodes[i]])
            included_nodes[nodes[i]] = True
            current_node_num += 1
        elif operations[i] == 'remove':
            if current_node_num <= 8:
                continue
            if included_nodes.get(nodes[i]) is not None:
                trace.append([seconds[i], operations[i], nodes[i]])
                current_node_num -= 1
                included_nodes.pop(nodes[i])
    return trace

def rewrite_node_number(trace):
    node_nums = 0
    node_map = {}
    for line in trace:
        if line[1] == 'add':
            node_nums += 1
            node_map[line[2]] = 'node' + str(node_nums)
            line[2] = 'node' + str(node_nums)
        elif line[1] == 'remove':
            line[2] = node_map[line[2]]
    return trace

def regenerate_trace(trace, file):
    with open(file, 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile)
        for line in trace:
            spamwriter.writerow(line)

def generate_trace_8_24(file_raw, file_target):
    seconds, operations, nodes = read_trace(file_raw)
    trace = modify_trace(seconds, operations, nodes)
    print(trace)
    after_rewrite_trace = rewrite_node_number(trace)
    print(after_rewrite_trace)
    regenerate_trace(after_rewrite_trace, file_target)


# generate_trace_16('simulator/traces/g4dn-trace.csv', 'simulator/traces/g4dn-trace-16.csv')
generate_trace_8_24('simulator/traces/p3-trace.csv', 'simulator/traces/p3-trace-8-24.csv')


'''
16 nodes handler
'''
def plot_nodes_samples(seconds, nodes_samples, prefix):
    fig, ax = plt.subplots()
    new_seconds, new_nodes = [], []
    for idx, second in enumerate(seconds):
        new_seconds.append(second)
        new_nodes.append(nodes_samples[idx])
        if idx < len(seconds) - 1:
            new_seconds.append(seconds[idx + 1])
            new_nodes.append(nodes_samples[idx])
    ax.plot(new_seconds, new_nodes)
    ax.set_ylim(0, max(nodes_samples) + 1)
    fig.tight_layout()
    fig.savefig(f'simulator/traces/{prefix}_nodes_samples.png')


def calculate_stats_nodes(file):
    seconds, operations, nodes, nodes_samples = [], [], [], []
    if file.endswith(".csv"):
        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                seconds.append(int(row[0]))
                operations.append(row[1])
                nodes.append(row[2])
    current_nodes = 0
    seconds_norepeat = []
    for i in range(0, len(seconds)):
        if len(seconds_norepeat) > 0 and seconds_norepeat[-1] != seconds[i]:
            nodes_samples.append(current_nodes)
            seconds_norepeat.append(seconds[i])
        if operations[i] == 'add':
            current_nodes += 1
        elif operations[i] == 'remove':
            current_nodes -= 1
        if len(seconds_norepeat) == 0:
            seconds_norepeat.append(seconds[i])
    nodes_samples.append(current_nodes)
    print(dict(zip(seconds_norepeat, nodes_samples)))
    plot_nodes_samples(seconds_norepeat, nodes_samples, file.split('/')[-1].split('-')[0])
    return max(nodes_samples), min(nodes_samples), statistics.mean(nodes_samples)

# print(calculate_stats_nodes('simulator/traces/g4dn-trace.csv'))
print(calculate_stats_nodes('simulator/traces/p3-trace-8-24.csv'))

# print(calculate_stats_nodes('simulator/traces/g4dn-trace-16.csv'))
# print(calculate_stats_nodes('simulator/traces/p3-trace-16.csv'))
    