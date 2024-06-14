from pssh.clients import ParallelSSHClient, SSHClient

localhost = 'localhost'
localhostclient = SSHClient(localhost, pkey='~/.ssh/id_rsa', user='gaoziyuan', password='gzy2024')

output = localhostclient.run_command('etcdctl rm --dir --recursive /torchelastic')

hosts = ['localhost', '10.20.23.91', '10.20.23.92', '10.20.23.46']
all_hosts = []

clients_all = ParallelSSHClient(hosts, pkey='~/.ssh/id_rsa', user='gaoziyuan', password='gzy2024')



def preparation():
    output = clients_all.run_command('docker build -t torchelastic .')
