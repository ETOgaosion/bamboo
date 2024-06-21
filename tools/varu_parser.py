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


iteration_time_parser                  = re.compile(r'iteration(\s+)(?P<iterationnum>\d+)/(.+)\| elapsed time per iteration \(ms\): (?P<iterationtime>.+) \| learning rate')
checkpt_time_parser                  = re.compile(r'save checkpoint: (?P<checkpttime>.+)s')

def res_parser(file):
    print(f'processing: {file}')
    first_iterations_time = []
    normal_iterations_time = []
    checkpt_time = []
    with open(file, 'r') as f:
        for line in f:
            iteration_time_match = iteration_time_parser.search(line)
            checkpt_time_match = checkpt_time_parser.search(line)
            if iteration_time_match:
                iterationnum = int(iteration_time_match.group('iterationnum'))
                if iterationnum % 5 == 1:
                    first_iterations_time.append(float(iteration_time_match.group('iterationtime')))
                else:
                    normal_iterations_time.append(float(iteration_time_match.group('iterationtime')))
            if checkpt_time_match:
                checkpt_time.append(float(checkpt_time_match.group('checkpttime')))
    return statistics.mean(first_iterations_time), statistics.mean(normal_iterations_time), statistics.mean(checkpt_time)


print(res_parser('simulator/data/varu/ssh_out_0.log'))