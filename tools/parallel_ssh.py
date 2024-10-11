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
gpus_per_nodes = 4
# required_nodes = [4, 8, 12, 16, 20, 24]
# required_nodes = [16, 20, 24, 28, 32]
required_nodes = [8, 10, 12, 14, 16, 18, 20]
# required_pipeline_parallel_size = 4
required_pipeline_parallel_size = [4, 5, 4, 2, 4, 3, 5, 11, 4]
required_data_parallel_size = []
for i, node_i in enumerate(required_nodes):
    required_data_parallel_size.append(node_i // required_pipeline_parallel_size[i])
# required_data_parallel_size = [1, 2, 2, 4, 2, 4]
# required_data_parallel_size = [1, 2, 2, 4, 2, 4, 4, 8, 4, 8]
# required_micro_batch_size = [1, 2, 2, 2, 4, 1]
# required_micro_batch_size = [2, 2, 4, 4, 4]
required_micro_batch_size = [2, 2, 2, 1, 2, 2, 2, 4, 1]
sequence_len = 1024

hosts = ['localhost', '10.20.23.91', '10.20.23.92', '10.20.23.46', '10.20.23.42', '10.20.23.47']
# hosts = ['localhost', '10.20.23.91', '10.20.23.92', '10.20.23.46']
localhost_ip = '10.20.23.90'
project_dir = '/home/gaoziyuan/project/bamboo'
user = 'gaoziyuan'
password = 'gzy2024'
pkey = '/home/gaoziyuan/.ssh/id_rsa'


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
    output = localhostclient.run_command('etcdctl rm --dir --recursive /torchelastic')
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
    output_docker = clients_hosts.run_command('cd ' + project_dir + ' && docker build -t whatcanyousee/bamboo .')
    clients_hosts.join(output_git_pull)
    clients_hosts.join(output_docker)

# preparation()

def kill_all():
    for host in seperate_clients_hosts:
        print(host)
        output = host.run_command('ps aux | grep project_pactum | grep -v grep | awk "{print \$2}" | sudo xargs kill -9 ', sudo=True)
        for host_out in output:
            host_out.stdin.write('gzy2024\n')
            host_out.stdin.flush()
        host.join(output)
        for line in host_out.stdout:
            print(line)
        for line in host_out.stderr:
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

for k, nodes in enumerate(required_nodes):
    all_hosts[nodes] = []
    all_clients[nodes] = []
    all_commands[nodes] = []
    cards_number[nodes] = []
    
    required_hosts_int = (nodes // gpus_per_nodes)
    required_hosts_left = (nodes % gpus_per_nodes)
    required_hosts = math.ceil(nodes / gpus_per_nodes)
    
    if nodes == 4:
        for i in range(required_hosts_left):
            all_hosts[nodes].append(hosts[required_hosts - 1])
            all_clients[nodes].append(clients[hosts[required_hosts - 1]][i])
            all_commands[nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-master-pssh.sh ' + 
                                        str(i) + ' ' +                                           # cur gpu
                                        str(nodes) + ' ' +                                       # num nodes
                                        str(required_pipeline_parallel_size[k]) + ' ' +     # num stages
                                        str(required_hosts_int * gpus_per_nodes + i) + ' ' +     # global rank
                                        str(required_micro_batch_size[k]) + ' ' +                # micro batch size
                                        str(sequence_len))                                       # sequence len
        continue
        
    for i in range(required_hosts_int):
        all_hosts[nodes].extend([hosts[i]] * gpus_per_nodes)
        all_clients[nodes].extend(clients[hosts[i]])
        for j in range(gpus_per_nodes):
            role = 'slave'
            if i == 0:
                role = 'master'
            all_commands[nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-' + role + '-pssh.sh ' + 
                                       str(j) + ' ' +                                           # cur gpu
                                       str(nodes) + ' ' +                                       # num nodes
                                       str(required_pipeline_parallel_size[k]) + ' ' +     # num stages
                                       str(i * gpus_per_nodes + j) + ' ' +                      # global rank
                                       str(required_micro_batch_size[k]) + ' ' +                # micro batch size
                                       str(sequence_len))                                       # sequence len
    for i in range(required_hosts_left):
        all_hosts[nodes].append(hosts[required_hosts - 1])
        # skip 47 GPU 1
        if required_hosts == len(hosts):
            if i == 1:
                i += 1
                all_clients[nodes].append(clients[hosts[required_hosts - 1]][i])
                all_commands[nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-slave-pssh.sh ' + 
                                            str(i) + ' ' +                                           # cur gpu
                                            str(nodes) + ' ' +                                       # num nodes
                                            str(required_pipeline_parallel_size[k]) + ' ' +     # num stages
                                            str(required_hosts_int * gpus_per_nodes + i - 1) + ' ' +     # global rank
                                            str(required_micro_batch_size[k]) + ' ' +                # micro batch size
                                            str(sequence_len))                                       # sequence len
                break
        all_clients[nodes].append(clients[hosts[required_hosts - 1]][i])
        all_commands[nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-slave-pssh.sh ' + 
                                    str(i) + ' ' +                                           # cur gpu
                                    str(nodes) + ' ' +                                       # num nodes
                                    str(required_pipeline_parallel_size[k]) + ' ' +     # num stages
                                    str(required_hosts_int * gpus_per_nodes + i) + ' ' +     # global rank
                                    str(required_micro_batch_size[k]) + ' ' +                # micro batch size
                                    str(sequence_len))                                       # sequence len
    cards_number[nodes] = [gpus_per_nodes] * required_hosts_int
    if required_hosts_left != 0:
        cards_number[nodes].append(required_hosts_left)

pprint.pp(all_hosts)
pprint.pp(all_commands)
pprint.pp(cards_number)


'''
Execution of commands
'''
def execute_command(nodes):
    output = []
    clear_etcd()
    print('execute ', all_hosts[nodes], all_commands[nodes])
    for k, client in enumerate(all_clients[nodes]):
        output.append(client.run_command(all_commands[nodes][k]))
    for k, client in enumerate(all_clients[nodes]):
        client.wait_finished(output[k])
    for out in output:
        for line in out.stdout:
            print(line)
        for line in out.stderr:
            print(line)
    print('Finish ', nodes, ' nodes')

# execute_command(2)
execute_command(8)
# execute_command(10)
# execute_command(12)
# execute_command(14)
# execute_command(16)
# execute_command(18)
# execute_command(20)
# execute_command(22)
# execute_command(24)
# execute_command(32)

# for nodes in required_nodes:
#     execute_command(nodes)

# kill_all()