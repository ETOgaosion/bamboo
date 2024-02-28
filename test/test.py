import etcd
import json

client = etcd.Client()
client.write('torchelastic/p2p/run_encoder/rdzv/active_version', json.dumps({"status": "setup"}), prevExist=False, ttl=5)

print(client.get('torchelastic/p2p/run_encoder/rdzv/active_version').value)