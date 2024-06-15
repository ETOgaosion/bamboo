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

def mmodify_trace(seconds, operations, nodes):
    trace = []
    current_node_num = 0
    included_nodes = {}
    for i in range(len(seconds)):
        if operations[i] == 'add' and current_node_num < 16:
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

def generate_trace_16(file_raw, file_target):
    seconds, operations, nodes = read_trace(file_raw)
    trace = mmodify_trace(seconds, operations, nodes)
    print(trace)
    after_rewrite_trace = rewrite_node_number(trace)
    print(after_rewrite_trace)
    regenerate_trace(after_rewrite_trace, file_target)


generate_trace_16('traces/g4dn-trace.csv', 'traces/g4dn-trace-16.csv')
generate_trace_16('traces/p3-trace.csv', 'traces/p3-trace-16.csv')


'''
16 nodes handler
'''
def plot_nodes_samples(nodes_samples):
    fig, ax = plt.subplots()
    ax.bar(range(len(nodes_samples)), nodes_samples)
    fig.tight_layout()
    fig.savefig('traces/nodes_samples.png')


def calculate_avg_nodes(file):
    seconds, operations, nodes_samples = [], [], []
    if file.endswith(".csv"):
        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                seconds.append(int(row[0]))
                operations.append(row[1])
    current_nodes = 0
    last_time = 0
    for i in range(1, len(seconds)):
        if operations[i] == 'add':
            current_nodes += 1
        elif operations[i] == 'remove':
            current_nodes -= 1
        if seconds[i] - last_time >= 10000:
            nodes_samples.append(current_nodes)
            last_time = seconds[i]
    plot_nodes_samples(nodes_samples)
    return statistics.mean(nodes_samples)

print(calculate_avg_nodes('traces/g4dn-trace-16.csv'))
# calculate_avg_nodes('traces/p3-trace-16.csv')
    