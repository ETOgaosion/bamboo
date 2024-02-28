import os
import signal
import time
import sys
import json
import matplotlib.pyplot as plt
import random
import logging

_log_fmt = logging.Formatter("%(levelname)s %(asctime)s %(message)s")
_log_handler = logging.StreamHandler(sys.stderr)
_log_handler.setFormatter(_log_fmt)

log = logging.getLogger(__name__)
log.propagate = False
log.setLevel(logging.INFO)
log.addHandler(_log_handler)

logger = logging.getLogger('project_pactum.etcd')

# define a funtion to read data from spot-advicer-data.json in this directory(use system package to generate the path, do not use hard code), read data into python datastructure
def read_data():
    file_path = os.path.join(sys.path[0], 'data/spot-advisor-data.json')
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

avg = 0

def calc_avg_r():
    if avg == 0:
        data = read_data()
        size = 0
        total = 0
        for instances in data["spot_advisor"]:
            for OS in data["spot_advisor"][instances]:
                for inst_type in data["spot_advisor"][instances][OS]:
                    size += 1
                    total += data["spot_advisor"][instances][OS][inst_type]["r"]
        avg = total/size
        print(avg)
        logger.info(f'avg:{avg}')
    return avg

def check_for_preemption():
    while True:
        rand = random.uniform(0, 1)
        if rand <= 1:
            logger.info(str(time.time()) + ", " + str(rand) + ", Preemption detected\n")
            os.kill(os.getpid(), signal.SIGTERM)

        time.sleep(3)