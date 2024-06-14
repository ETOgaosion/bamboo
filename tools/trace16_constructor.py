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
        seconds, operations, nodes, nodes_map = [], [], [], {}
        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                seconds.append(row[0])
                operations.append(row[1])
                nodes.append(row[2])
                nodes_map[int(row[2][4:])] = True
        return seconds, operations, nodes, nodes_map
    

seconds, operations, nodes, nodes_map = read_trace('traces/g4dn-trace.csv')
# seconds, operations, nodes, nodes_map = read_trace('traces/p3-trace.csv')

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
            if included_nodes.get(nodes[i]) is not None:
                trace.append([seconds[i], operations[i], nodes[i]])
                current_node_num -= 1
                included_nodes.pop(nodes[i])
    return trace

trace = mmodify_trace(seconds, operations, nodes)
print(trace)

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

after_rewrite_trace = rewrite_node_number(trace)
print(after_rewrite_trace)

def regenerate_trace(trace, file):
    with open(file, 'w', newline='') as csvfile:
        spamwriter = csv.writer(csvfile)
        for line in trace:
            spamwriter.writerow(line)


regenerate_trace(after_rewrite_trace, 'traces/g4dn-trace-16.csv')
# regenerate_trace(after_rewrite_trace, 'traces/p3-trace-16.csv')