from torch.distributed.elastic.agent.server import Worker

class ProjectPactumWorker(Worker):

    def __init__(
        self,
        local_rank: int,
        global_rank: int = -1,
        role_rank: int = -1,
        world_size: int = -1,
        role_world_size: int = -1,
        active_pipe_parallel = None,
        redundant_pipe_parallel = None,
    ):
        super().__init__(local_rank, global_rank, role_rank, world_size, role_world_size)
        self.active_pipe_parallel = active_pipe_parallel
        self.redundant_pipe_parallel = redundant_pipe_parallel