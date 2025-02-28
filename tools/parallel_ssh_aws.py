import time
from pssh.clients import ParallelSSHClient, SSHClient
import pprint
import math
import signal
import sys

'''
Hint: Modify these Configurations only
All functions are extendable
'''
gpus_per_nodes = 8
model_sizes = ['1.3B', '2.7B', '6.7B', '13B']
# required_nodes = [4, 8, 12, 16, 20, 24]
# required_nodes = [16, 20, 24, 28, 32]
# # required_nodes = [8, 10, 12, 14, 16, 18, 20]
# required_nodes = {'350M': [8],
#                 '1.3B': [8],
#                 '2.7B': [8],
#                 '6.7B': [8],
#                 '13B': [8]}
required_nodes = {'350M': [8, 10, 12, 14, 16],
                '1.3B': [8, 10, 12, 14, 16],
                '2.7B': [8, 10, 12, 14, 16],
                '6.7B': [8, 10, 12, 14, 16],
                '13B': [8, 10, 12, 14, 16]}
# required_nodes = {'350M': [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32],
#                 '1.3B': [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32],
#                 '2.7B': [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32],
#                 '6.7B': [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32],
#                 '13B': [8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32]}
# required_pipeline_parallel_size = 4
required_pipeline_parallel_size = {'350M': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                                    '1.3B': [4, 5, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], 
                                    '2.7B': [8, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                    '6.7B': [4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                                    '13B': [4, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]}
required_data_parallel_size = {'350M': [], 
                                '1.3B': [], 
                                '2.7B': [], 
                                '6.7B': [], 
                                '13B': [], 
                                '30B': []}
for model_size in model_sizes:
    for i, node_i in enumerate(required_nodes[model_size]):
        required_data_parallel_size[model_size].append(node_i // required_pipeline_parallel_size[model_size][i])
# required_data_parallel_size = [1, 2, 2, 4, 2, 4]
# required_data_parallel_size = [1, 2, 2, 4, 2, 4, 4, 8, 4, 8]
# required_micro_batch_size = [1, 2, 2, 2, 4, 1]
# required_micro_batch_size = [2, 2, 4, 4, 4]
required_micro_batch_size = {'350M': [32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32, 32],
                            '1.3B': [1, 2, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4], 
                            '2.7B': [1, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8], 
                            '6.7B': [1, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4], 
                            '13B': [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]}
sequence_len = 1024

# hosts = ['localhost', '10.20.23.91', '10.20.23.92', '10.20.23.46', '10.20.23.42', '10.20.23.47']
hosts = ['localhost']
hosts = ['localhost', '172.31.37.190']
# hosts = ['localhost', '172.31.37.190', '172.31.37.190', '172.31.37.190']
localhost_ip = '172.31.45.44'
project_dir = '/home/ubuntu/projects/bamboo'
user = 'ubuntu'
password = ''
pkey = '/home/ubuntu/.ssh/id_rsa'


'''
input check
'''
# assert len(required_nodes) == len(required_data_parallel_size) == len(required_micro_batch_size)


'''
preparations
'''
localhost = 'localhost'
localhostclient = SSHClient(localhost, pkey=pkey, user=user, password=password)

def clear_etcd():
    output = localhostclient.run_command(project_dir + '/etcd/etcdctl rm --dir --recursive /torchelastic')
    localhostclient.wait_finished(output)
    for line in output.stdout:
        print(line)
    for line in output.stderr:
        print(line)

clients_hosts = ParallelSSHClient(hosts, pkey=pkey, user=user, password=password)
seperate_clients_hosts = []
for host in hosts:
    seperate_clients_hosts.append(ParallelSSHClient([host], pkey=pkey, user=user, password=password))

def preparation():
    output_git_pull = clients_hosts.run_command('cd ' + project_dir + ' && git pull origin main')
    clients_hosts.join(output_git_pull)

# preparation()

def kill_all():
    for host in seperate_clients_hosts:
        print(host)
        output = host.run_command('ps aux | grep project_pactum | grep -v grep | awk "{print \$2}" | sudo xargs kill -9 ', sudo=True)
        # for host_out in output:
        #     host_out.stdin.write('gzy2024\n')
        #     host_out.stdin.flush()
        host.join(output)
        for line in output.stdout:
            print(line)
        for line in output.stderr:
            print(line)
    
# kill_all()

def signal_handler(sig, frame):
    kill_all()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

clients = {}
for host in hosts:
    clients[host] = [SSHClient(host, pkey=pkey, user=user, password=password)] * gpus_per_nodes


'''
Preparation of clients and commands
'''
all_hosts = {}
all_clients = {}
all_commands = {}
cards_number = {}

for model_size in model_sizes:
    all_hosts[model_size] = {}
    all_clients[model_size] = {}
    all_commands[model_size] = {}
    cards_number[model_size] = {}
    for k, nodes in enumerate(required_nodes[model_size]):
        all_hosts[model_size][nodes] = []
        all_clients[model_size][nodes] = []
        all_commands[model_size][nodes] = []
        cards_number[model_size][nodes] = []
        
        required_hosts_int = (nodes // gpus_per_nodes)
        required_hosts_left = (nodes % gpus_per_nodes)
        required_hosts = math.ceil(nodes / gpus_per_nodes)
            
        for i in range(required_hosts_int):
            all_hosts[model_size][nodes].extend([hosts[i]] * gpus_per_nodes)
            all_clients[model_size][nodes].extend(clients[hosts[i]])
            for j in range(gpus_per_nodes):
                role = 'slave'
                if i == 0:
                    role = 'master'
                all_commands[model_size][nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-' + role + '-pssh-aws.sh ' + 
                                        str(j) + ' ' +                                           # cur gpu
                                        str(nodes) + ' ' +                                       # num nodes
                                        str(required_pipeline_parallel_size[model_size][k]) + ' ' +     # num stages
                                        str(i * gpus_per_nodes + j) + ' ' +                      # global rank
                                        str(required_micro_batch_size[model_size][k]) + ' ' +                # micro batch size
                                        str(sequence_len) + ' ' +                                # sequence len
                                        str(model_size))                                   # model size
        for i in range(required_hosts_left):
            all_hosts[model_size][nodes].append(hosts[required_hosts - 1])
            all_clients[model_size][nodes].append(clients[hosts[required_hosts - 1]][i])
            all_commands[model_size][nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-slave-pssh-aws.sh ' + 
                                        str(i) + ' ' +                                           # cur gpu
                                        str(nodes) + ' ' +                                       # num nodes
                                        str(required_pipeline_parallel_size[model_size][k]) + ' ' +     # num stages
                                        str(required_hosts_int * gpus_per_nodes + i) + ' ' +     # global rank
                                        str(required_micro_batch_size[model_size][k]) + ' ' +                # micro batch size
                                        str(sequence_len) + ' ' +                                # sequence len
                                        str(model_size))                                   # model size
        cards_number[nodes] = [gpus_per_nodes] * required_hosts_int
        if required_hosts_left != 0:
            cards_number[nodes].append(required_hosts_left)

# pprint.pp(all_hosts)
pprint.pp(all_commands)
# pprint.pp(cards_number)


'''
Execution of commands
'''
def execute_command(model_size, nodes):
    output = []
    clear_etcd()
    print('execute ', all_hosts[model_size][nodes], all_commands[model_size][nodes])
    for k, client in enumerate(all_clients[model_size][nodes]):
        output.append(client.run_command(all_commands[model_size][nodes][k]))
    for k, client in enumerate(all_clients[model_size][nodes]):
        client.wait_finished(output[k])
    for out in output:
        for line in out.stdout:
            print(line)
        for line in out.stderr:
            print(line)
    print('Finish ', nodes, ' nodes')

execute_command('1.3B', 10)
# execute_command('2.7B', 8)
# execute_command('1.3B', 8)
# execute_command('1.3B', 8)

# kill_all()
