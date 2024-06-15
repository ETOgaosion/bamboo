from pssh.clients import ParallelSSHClient, SSHClient
import pprint
import math

'''
Hint: Modify these Configurations only
All functions are extendable
'''
gpus_per_nodes = 4
required_nodes = [8, 10, 12, 14, 16]
# required_nodes = [8, 10, 12, 14, 16, 20, 24, 28, 32]
required_data_parallel_size = [2, 2, 4, 2, 4]
# required_data_parallel_size = [2, 2, 4, 2, 4, 4, 8, 4, 8]
required_micro_batch_size = [4, 8, 3, 8, 8]
# required_micro_batch_size = [4, 8, 3, 8, 8, 16, 8, 16, 16]
hosts = ['localhost', '10.20.23.91', '10.20.23.92', '10.20.23.46']
localhost_ip = '10.20.23.90'
project_dir = '/home/gaoziyuan/project/bamboo'
user = 'gaoziyuan'
password = 'gzy2024'
pkey = '/home/gaoziyuan/.ssh/id_rsa'


'''
input check
'''
assert len(required_nodes) == len(required_data_parallel_size) == len(required_micro_batch_size)


'''
preparations
'''
localhost = 'localhost'
localhostclient = SSHClient(localhost, pkey=pkey, user=user, password=password)

def clear_etcd():
    localhostclient.run_command('etcdctl rm --dir --recursive /torchelastic')

clients_hosts = ParallelSSHClient(hosts, pkey=pkey, user=user, password=password)

def preparation():
    clients_hosts.run_command('cd ' + project_dir + ' && git pull origin main')
    clients_hosts.run_command('cd ' + project_dir + ' && docker build -t torchelastic .')

# preparation()

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
    
    for i in range(required_hosts_int):
        all_hosts[nodes].extend([hosts[i]] * gpus_per_nodes)
        all_clients[nodes].extend(clients[hosts[i]])
        for j in range(gpus_per_nodes):
            role = 'slave'
            if i == 0:
                role = 'master'
            all_commands[nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-' + role + '.sh ' + 
                                       str(j) + ' ' +                                           # cur gpu
                                       str(nodes) + ' ' +                                       # num nodes
                                       str(nodes // required_data_parallel_size[k]) + ' ' +     # num stages
                                       str(i * gpus_per_nodes + j) + ' ' +                      # global rank
                                       str(required_micro_batch_size[k]))                       # micro batch size
    for i in range(required_hosts_left):
        all_hosts[nodes].append(hosts[required_hosts - 1])
        all_clients[nodes].append(clients[hosts[required_hosts - 1]][i])
        all_commands[nodes].append('cd ' + project_dir + ' && ./scripts/run-project-pactum-docker-slave.sh ' + 
                                    str(i) + ' ' +                                           # cur gpu
                                    str(nodes) + ' ' +                                       # num nodes
                                    str(nodes // required_data_parallel_size[k]) + ' ' +     # num stages
                                    str(required_hosts_int * gpus_per_nodes + i) + ' ' +     # global rank
                                    str(required_micro_batch_size[k]))                       # micro batch size
    cards_number[nodes] = [gpus_per_nodes] * required_hosts_int
    if required_hosts_left != 0:
        cards_number[nodes].append(required_hosts_left)

pprint.pp(all_hosts)
pprint.pp(all_commands)
pprint.pp(cards_number)


'''
Execution of commands
'''
for nodes, clients in all_clients.items():
    output = []
    clear_etcd()
    for k, client in enumerate(clients):
        print(all_hosts[nodes][k], ' execute ', all_commands[nodes][k])
        output.append(client.run_command(all_commands[nodes][k]))
    for k, client in enumerate(clients):
        client.wait_finished(output[k])
    print('Finish ', nodes, ' nodes')
    