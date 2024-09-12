import copy
import math
from typing import List
import argparse

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import datetime


PAD_IDX = 0

def report_memory(name, get_list=False):
    """Simple GPU memory report."""

    mega_bytes = 1024.0 * 1024.0
    allocated = torch.cuda.memory_allocated() / mega_bytes
    max_allocated = torch.cuda.max_memory_allocated() / mega_bytes
    reserved = torch.cuda.memory_reserved() / mega_bytes
    max_reserved = torch.cuda.max_memory_reserved() / mega_bytes

    string = f'{datetime.datetime.now()} - ' + name + ' memory (MB)'
    string += ' | allocated: {}'.format(allocated)
    string += ' | max allocated: {}'.format(max_allocated)
    string += ' | reserved: {}'.format(reserved)
    string += ' | max reserved: {}'.format(max_reserved)
    
    print(string)

    if get_list:
        mem_to_csv = [["allocated", "max_allocated", "reserved", "max_reserved"], 
            [f"{allocated:.2f}", f"{max_allocated:.2f}", f"{reserved:.2f}", f"{max_reserved:.2f}"]]
        return string, mem_to_csv

    return string


def clones(module, N):
    "Produce N identical layers."
    return nn.ModuleList([copy.deepcopy(module) for _ in range(N)])


class DecoderLayerSimple(nn.Module):
    def __init__(self, size, self_attn, src_attn, feed_forward, dropout):
        super().__init__()
        self.size = size
        self.self_attn = self_attn
        self.src_attn = src_attn
        self.feed_forward = feed_forward
        self.sublayer = clones(SublayerConnection(size, dropout), 3)

    def forward(self, x):
        "Follow Figure 1 (right) for connections."
        m = torch.sqrt(1 - x)  # We can not handle more than one input, so just generate a random one here
        x = self.sublayer[0](x, lambda x: self.self_attn(x, x, x))
        x = self.sublayer[1](x, lambda x: self.src_attn(x, m, m))
        return self.sublayer[2](x, self.feed_forward)


class LayerNorm(nn.Module):
    "Construct a layernorm module (See citation for details)."
    def __init__(self, features, eps=1e-6):
        super(LayerNorm, self).__init__()
        self.a_2 = nn.Parameter(torch.ones(features))
        self.b_2 = nn.Parameter(torch.zeros(features))
        self.eps = eps

    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        std = x.std(-1, keepdim=True)
        return self.a_2 * (x - mean) / (std + self.eps) + self.b_2


class SublayerConnection(nn.Module):
    """
    A residual connection followed by a layer norm.
    Note for code simplicity the norm is first as opposed to last.
    """
    def __init__(self, size, dropout):
        super(SublayerConnection, self).__init__()
        self.norm = LayerNorm(size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, sublayer):
        "Apply residual connection to any sublayer with the same size."
        return x + self.dropout(sublayer(self.norm(x)))


def attention(query, key, value, mask=None, dropout=None):
    "Compute 'Scaled Dot Product Attention'"
    d_k = query.size(-1)
    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, -1e9)
    p_attn = F.softmax(scores, dim = -1)
    if dropout is not None:
        p_attn = dropout(p_attn)
    return torch.matmul(p_attn, value), p_attn


class MultiHeadedAttention(nn.Module):
    def __init__(self, h, d_model, dropout=0.1):
        "Take in model size and number of heads."
        super(MultiHeadedAttention, self).__init__()
        # We assume d_v always equals d_k
        assert d_model % h == 0
        self.d_k = d_model // h
        self.h = h
        self.linears = clones(nn.Linear(d_model, d_model), 4)
        self.attn = None
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, query, key, value, mask=None):
        "Implements Figure 2"
        if mask is not None:
            # Same mask applied to all h heads.
            mask = mask.unsqueeze(1)
        nbatches = query.size(0)

        # 1) Do all the linear projections in batch from d_model => h x d_k
        query, key, value = \
            [l(x).view(nbatches, -1, self.h, self.d_k).transpose(1, 2)
             for l, x in zip(self.linears, (query, key, value))]

        # 2) Apply attention on all the projected vectors in batch.
        x, self.attn = attention(query, key, value, mask=mask,
                                 dropout=self.dropout)

        # 3) "Concat" using a view and apply a final linear.
        x = x.transpose(1, 2).contiguous() \
             .view(nbatches, -1, self.h * self.d_k)
        return self.linears[-1](x)


class PositionwiseFeedForward(nn.Module):
    "Implements FFN equation."
    def __init__(self, d_model, d_ff, dropout=0.1):
        super().__init__()
        self.w_1 = nn.Linear(d_model, d_ff)
        self.w_2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        return self.w_2(self.dropout(F.relu(self.w_1(x))))


class GPT3Simple(nn.Module):
    def __init__(self, N=96, d_model=12288, d_ff=2048, h=8, dropout=0.1):
        """ A simplified bert without embedding and language model heads """
        super().__init__()
        c = copy.deepcopy

        attn = MultiHeadedAttention(h, d_model)
        ff = PositionwiseFeedForward(d_model, d_ff, dropout)
        layer = DecoderLayerSimple(d_model, c(attn), c(attn), c(ff), dropout)
        self.layers = clones(layer, N)
        self.norm = LayerNorm(layer.size)
        self.reduce = lambda x: x.sum(-1)

    def forward(self, x):
        """
        Args:
            x (Tensor[batch size, sequence length, d_model]): input after encoder

        Returns:
            out ()
        """
        for layer in self.layers:
            x = layer(x)
        return self.reduce(self.norm(x))

    def join_layers(self):
        return [i for i in self.layers] + [self.norm, self.reduce]


def make_model(*args):
    return GPT3Simple(*args)


def test():
    device = 'cuda:0'

    d_model = 32
    d_ff = 64
    n_layer = 4
    model = make_model(n_layer, d_model, d_ff).to(device)

    batch_size = 4
    seq_len = 12
    x = torch.randn(batch_size, seq_len, d_model).to(device)

    out = model(x)
    print(f'Input shape: {x.shape}; \n'
          f'Output shape: {out.shape}')


def train():
    import deepspeed
    from deepspeed.pipe import PipelineModule
    from deepspeed.runtime.pipe.topology import PipeDataParallelTopology

    def get_args():
        parser = argparse.ArgumentParser(description='FFN')
        parser.add_argument('-s',
                            '--steps',
                            type=int,
                            default=10,
                            help='quit after this many steps')
        parser.add_argument('--curr-step', '-cs',
                            type=int,
                            default=0,
                            help='The step to start on')
        parser.add_argument('--backend',
                            type=str,
                            default='nccl',
                            help='distributed backend')

        ## Elastic stuff
        parser.add_argument('-rl', '--redundancy_level',
                            type=int,
                            default=0)
        parser.add_argument('--eager',
                            action='store_true',
                            default=False)
        parser.add_argument('--debug',
                            action='store_true',
                            default=False)
        parser.add_argument('--mem_log',
                            action='store_true',
                            default=False)
        parser.add_argument('--seed', type=int, default=1138, help='PRNG seed')

        # Model config args
        # GPT-3 6.7B
        # parser.add_argument('-N', type=int, default=32)
        # parser.add_argument('--d-model', '-dm', type=int, default=4096)
        # parser.add_argument('--d-ff', '-dff', type=int, default=16384)
        # parser.add_argument('-H', type=int, default=32)
        # parser.add_argument('--d-head', type=int, default=128)
        
        # GPT-3 2.7B
        # parser.add_argument('-N', type=int, default=32)
        # parser.add_argument('--d-model', '-dm', type=int, default=2560)
        # parser.add_argument('--d-ff', '-dff', type=int, default=10240)
        # parser.add_argument('-H', type=int, default=32)
        # parser.add_argument('--d-head', type=int, default=80)
        
        # GPT-3 XL
        parser.add_argument('-N', type=int, default=24)
        parser.add_argument('--d-model', '-dm', type=int, default=2048)
        parser.add_argument('--d-ff', '-dff', type=int, default=8192)
        parser.add_argument('-H', type=int, default=16)
        parser.add_argument('--d-head', type=int, default=128)
        
        # GPT-3 Medium
        # parser.add_argument('-N', type=int, default=24)
        # parser.add_argument('--d-model', '-dm', type=int, default=1024)
        # parser.add_argument('--d-ff', '-dff', type=int, default=4096)
        # parser.add_argument('-H', type=int, default=16)
        # parser.add_argument('--d-head', type=int, default=64)
        
        # GPT-3 Small
        # parser.add_argument('-N', type=int, default=12)
        # parser.add_argument('--d-model', '-dm', type=int, default=768)
        # parser.add_argument('--d-ff', '-dff', type=int, default=3072)
        # parser.add_argument('-H', type=int, default=12)
        # parser.add_argument('--d-head', type=int, default=64)

        parser.add_argument('--seq', type=int, default=1024)
        parser.add_argument('--nodes', type=int, default=16)
        parser.add_argument('--parts',
                            type=str,
                            default='',
                            help='Specify number of layers for each partition; separated by comma like `1,2,2,3`')

        parser = deepspeed.add_config_arguments(parser)
        args = parser.parse_args()
        return args
    args = get_args()
    np.random.seed(args.seed)

    def init_dist(args):
        import json
        import os
        from torch.distributed.elastic.rendezvous import RendezvousParameters
        from project_pactum.rendezvous.etcd import create_rdzv_handler

        rdzv_backend = 'etcd-v2'
        rdzv_endpoint = os.environ['PROJECT_PACTUM_ENDPOINT']
        run_id = os.environ['PROJECT_PACTUM_RUN_ID']
        min_nodes = int(os.environ['PROJECT_PACTUM_MIN_NODES'])
        max_nodes = int(os.environ['PROJECT_PACTUM_MAX_NODES'])
        rdzv_configs = json.loads(os.environ['PROJECT_PACTUM_RDZV_CONFIGS'])
        rdzv_configs['last_call_timeout'] = 1
        rdzv_parameters = RendezvousParameters(
            backend=rdzv_backend,
            endpoint=rdzv_endpoint,
            run_id=run_id,
            min_nodes=min_nodes,
            max_nodes=max_nodes,
            **rdzv_configs,
        )
        rdzv_handler = create_rdzv_handler(rdzv_parameters)
        deepspeed.init_distributed(
            args.backend,
            rank=int(os.environ['RANK']),
            world_size=int(os.environ['WORLD_SIZE']),
            store=rdzv_handler.setup_kv_store())

        data_parallel_size = int(os.environ['PROJECT_PACTUM_NUM_PIPELINES'])
        pipe_parallel_size = int(os.environ['PROJECT_PACTUM_NUM_STAGES'])
        global_decision = rdzv_handler.get_global_decision()
        custom_topology = PipeDataParallelTopology(pipe_parallel_size, data_parallel_size, global_decision)
        return {'data_parallel_size': data_parallel_size,
                'pipe_parallel_size': pipe_parallel_size,
                'topo': custom_topology}
    dist_config = init_dist(args)

    def gen_parts(args):
        parts = []
        return parts
        if args.parts:
            parts = [int(p) for p in args.parts.split(',')]
            assert sum(parts) == args.N
            parts[-1] += 2
            parts = [0] + [sum(parts[:i]) + p for i, p in enumerate(parts)]
        elif args.nodes > 0:
            parts = [args.N // args.nodes] * args.nodes
            for i in range(args.N % args.nodes):
                parts[i] += 1
            parts[-1] += 2
            parts = [0] + [sum(parts[:i]) + p for i, p in enumerate(parts)]
        return parts
    parts = gen_parts(args)
    print(f'parts: {parts}')

    layers = make_model(args.N, args.d_model, args.d_ff, args.H).join_layers()
    model = PipelineModule(layers=layers,
                           loss_fn=nn.MSELoss(),
                           num_stages=dist_config['pipe_parallel_size'],
                           partition_method='uniform' if len(parts) == 0 else 'custom',
                           custom_partitions=parts,
                           topology=dist_config['topo'],
                           activation_checkpoint_interval=0)

    class DatasetSimple(torch.utils.data.Dataset):
        def __init__(self, seq, d_model, size=20):
            self._size = size
            self._inputs = np.random.randn(size, seq, d_model)
            self._labels = np.random.randn(size, seq)

        def __len__(self):
            return self._size

        def __getitem__(self, idx):
            return (torch.tensor(self._inputs[idx], dtype=torch.float16),
                    self._labels[idx].astype('float16'))
    dataset = DatasetSimple(args.seq, args.d_model)

    engine, _, _, _ = deepspeed.initialize(
        args=args,
        model=model,
        model_parameters=[p for p in model.parameters() if p.requires_grad],
        training_data=dataset,
        redundancy_level=args.redundancy_level,
        eager_recovery=args.eager)

    for i in range(engine.global_steps, args.steps):
        print(f'{datetime.datetime.now()} - START TRAIN {i}')
        engine.train_batch(debug=args.debug, mem_log=args.mem_log)
        # report_memory("iteration")
        print(f'{datetime.datetime.now()} - FINISH TRAIN {i}')
    print("finish all")


if __name__ == '__main__':
    train()
