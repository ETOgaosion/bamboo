import os
import sys
import json
import matplotlib.pyplot as plt

# define a funtion to read data from spot-advicer-data.json in this directory(use system package to generate the path, do not use hard code), read data into python datastructure
def read_data():
    file_path = os.path.join(sys.path[0], 'spot-advisor-data.json')
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data

data = read_data()

def calc_r():
    max_r = 0
    size = 0
    total = 0
    r_map = {}
    for instances in data["spot_advisor"]:
        for OS in data["spot_advisor"][instances]:
            for inst_type in data["spot_advisor"][instances][OS]:
                size += 1
                total += data["spot_advisor"][instances][OS][inst_type]["r"]
                if max_r < data["spot_advisor"][instances][OS][inst_type]["r"]:
                    max_r = data["spot_advisor"][instances][OS][inst_type]["r"]
                if (r_map.get(int(data["spot_advisor"][instances][OS][inst_type]["r"])) == None):
                    r_map[int(data["spot_advisor"][instances][OS][inst_type]["r"])] = 1
                else:
                    r_map[int(data["spot_advisor"][instances][OS][inst_type]["r"])] += 1
    print(max_r)
    print(total/size)
    plt.bar(r_map.keys(), r_map.values())
    plt.xlabel('r value')
    plt.ylabel('count')
    plt.savefig('r_value.png')
    plt.show()


calc_r()