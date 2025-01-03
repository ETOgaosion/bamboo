# https://pytorch.org/docs/stable/elastic/agent.html

import functools
import os
import json
import signal
import shutil
import sys
import tempfile
import threading
import time
import datetime
import random

from colorama import Fore

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import sqlite3

global should_stop
should_stop = False

def agent_set_time_to_kill():
    conn = sqlite3.connect('test.db')
    conn.execute('''
                UPDATE TIME_TO_KILL SET TIME_TO_KILL = TRUE WHERE ID = 1
                ''')
    conn.commit()
    conn.close()

def sig_handler(signum, frame):
    print(Fore.LIGHTCYAN_EX, 'Signal hander called with signal', signum, Fore.RESET)
    global should_stop
    should_stop = True

from torch.distributed.elastic.agent.server import (
    RunResult,
    SimpleElasticAgent,
    Worker,
    WorkerGroup,
    WorkerState,
)
from torch.distributed.elastic.agent.server.api import _RoleInstanceInfo
from torch.distributed.elastic.multiprocessing import start_processes, PContext
from torch.distributed.elastic.utils import macros
from torch.distributed.elastic.utils.logging import get_logger
from torch.distributed.elastic.metrics import put_metric

from project_pactum.agent.worker import ProjectPactumWorker
from torch.distributed.elastic.agent.server.api import WorkerSpec

DEFAULT_ROLE = "default"
log = get_logger()


class ProjectPactumAgent(SimpleElasticAgent):

    def __init__(
        self,
        spec: WorkerSpec,
        start_method="spawn",
        exit_barrier_timeout: float = 300,
        log_dir: Optional[str] = None,
        extra_env = None,
        probability = 0.016649590654474076
    ):
        super().__init__(spec, exit_barrier_timeout)
        self._start_method = start_method
        self._pcontext: Optional[PContext] = None
        rdzv_run_id = spec.rdzv_handler.get_run_id()
        self._log_dir = self._make_log_dir(log_dir, rdzv_run_id)
        self._extra_env = extra_env

        preemption_checker = threading.Thread(
            target=self.check_for_preemption
        )
        preemption_checker.daemon = True
        preemption_checker.start()


    def check_for_preemption(self):
        while True:
            pass
            
    def signal(self, signum, frame):
        role = self._worker_group.spec.role
        worker_pids = {w.id for w in self._worker_group.workers}
        assert self._pcontext is not None
        pc_pids = set(self._pcontext.pids().values())
        if worker_pids != pc_pids:
            log.error(
                f"[{role}] worker pids do not match process_context pids."
                f" Expected: {worker_pids}, actual: {pc_pids}"
            )
        # Kill the workers
        for pid in pc_pids:
            os.kill(pid, 15)

        from colorama import Fore
        print(Fore.RED + "ABOUT TO DIE!!!" + Fore.RESET)
        os.kill(os.getpid(), 9)

    def _make_log_dir(self, log_dir: Optional[str], rdzv_run_id: str):
        base_log_dir = log_dir or tempfile.mkdtemp(prefix="torchelastic_")
        os.makedirs(base_log_dir, exist_ok=True)
        dir = tempfile.mkdtemp(prefix=f"{rdzv_run_id}_", dir=base_log_dir)
        log.info(f"log directory set to: {dir}")
        return dir

    def _rendezvous(self, worker_group: WorkerGroup) -> None:
        r"""
        Runs rendezvous for the workers specified by worker spec.
        Assigns workers a new global rank and world size.
        Updates the rendezvous store for the worker group.
        """

        spec = worker_group.spec
        
        num_cycles = 0

        while True:
            store, group_rank, group_world_size, num_pipelines, num_stages, global_decision = spec.rdzv_handler.next_rendezvous()
            num_cycles += 1
            log.info(f'finish next rendezvous for index {num_cycles}')
            self._store = store

            # PROJECT-PACTUM: Lookup coordinates from global decision
            coordinates = []
            for info in global_decision:
                if info.rank == group_rank:
                    coordinates = info.active_coordinates

            # PROJECT-PACTUM: If it doesn't have any coordinates then we
            #                 shouldn't even start it, try again.
            if len(coordinates) != 0:
                break

        workers = self._assign_worker_ranks(store, group_rank, group_world_size, spec, num_pipelines, num_stages, global_decision, coordinates)
        
        log.info(f'after assign worker ranks, workers: {workers}')

        worker_group.workers = workers
        worker_group.store = store
        worker_group.group_rank = group_rank
        worker_group.group_world_size = group_world_size

        if group_rank == 0:
            self._set_master_addr_port(store, spec.master_addr, spec.master_port)
        master_addr, master_port = self._get_master_addr_port(store)
        restart_count = spec.max_restarts - self._remaining_restarts

        log.warning(
            f"[{spec.role}] {datetime.datetime.now()} Rendezvous complete for workers. Result:\n"
            f"  restart_count={restart_count}\n"
            f"  master_addr={master_addr}\n"
            f"  master_port={master_port}\n"
            f"  group_rank={group_rank}\n"
            f"  group_world_size={group_world_size}\n"
            f"  num_pipelines={num_pipelines}\n"
            f"  num_stages={num_stages}\n"
            f"  global_decision={global_decision}\n"
            f"  local_ranks={[worker.local_rank for worker in workers]}\n"
            f"  role_ranks={[worker.role_rank for worker in workers]}\n"
            f"  global_ranks={[worker.global_rank for worker in workers]}\n"
            f"  role_world_sizes={[worker.role_world_size for worker in workers]}\n"
            f"  global_world_sizes={[worker.world_size for worker in workers]}\n"
        )

    def _invoke_run(self, role: str = DEFAULT_ROLE) -> RunResult:
        # NOTE: currently only works for a single role

        spec = self._worker_group.spec
        role = spec.role

        log.info(
            f"[{role}] starting workers for entrypoint: {spec.get_entrypoint_name()}"
        )

        self._initialize_workers(self._worker_group)
        monitor_interval = spec.monitor_interval
        rdzv_handler = spec.rdzv_handler

        start = time.time()

        while True:
            assert self._worker_group.state != WorkerState.INIT
            time.sleep(monitor_interval)
            run_result = self._monitor_workers(self._worker_group)
            state = run_result.state
            self._worker_group.state = state

            put_metric(f"workers.{role}.remaining_restarts", self._remaining_restarts)
            put_metric(f"workers.{role}.{state.name.lower()}", 1)

            if state == WorkerState.SUCCEEDED:
                log.info(
                    f"[{role}] worker group successfully finished."
                    f" Waiting {self._exit_barrier_timeout} seconds for other agents to finish."
                )
                self._exit_barrier()
                return run_result
            elif state in {WorkerState.UNHEALTHY, WorkerState.FAILED}:
                log.info(f'self._remaining_restarts, {self._remaining_restarts}, spec.max_restarts, {spec.max_restarts}')
                # PROJECT-PACTUM: If any worker exited with the special code to
                #                 put it on standby, just restart the workers so
                #                 it does another rendezvous
                failures = run_result.failures
                exit_early = False
                for rank, failure in failures.items():
                    if failure.exitcode == 125:
                        self._restart_workers(self._worker_group)
                        exit_early = True
                        break
                if exit_early:
                    continue

                if self._remaining_restarts > 0:
                    log.info(
                        f"[{role}] Worker group {state.name}. "
                        f"{self._remaining_restarts}/{spec.max_restarts} attempts left;"
                        f" will restart worker group"
                    )
                    self._remaining_restarts -= 1
                    self._restart_workers(self._worker_group)
                else:
                    self._stop_workers(self._worker_group)
                    self._worker_group.state = WorkerState.FAILED
                    self._exit_barrier()
                    return run_result
            elif state == WorkerState.HEALTHY:
                pass
                # PROJECT-PACTUM: Do not restart the workers for joining nodes
                # # membership changes do not count as retries
                # num_nodes_waiting = rdzv_handler.num_nodes_waiting()
                # group_rank = self._worker_group.group_rank
                # if num_nodes_waiting > 0:
                #     log.info(
                #         f"[{role}] Detected {num_nodes_waiting} "
                #         f"new nodes from group_rank={group_rank}; "
                #         f"will restart worker group"
                #     )
                #     self._restart_workers(self._worker_group)
            else:
                raise Exception(f"[{role}] Worker group in {state.name} state")

    def _check_ready(self) -> bool:
        return self._pcontext is not None

    def _drain_preempting_workers(self, signum, frame):
        if self._pcontext is not None:
            for pid in self._pcontext.pids().values():
                log.info(f"Draining worker pid={pid} due to preemption")
                os.kill(pid, signal.SIGTERM)

    def _assign_worker_ranks(
        self, store, group_rank: int, group_world_size: int, spec: WorkerSpec,
        num_pipelines, num_stages, global_decision, coordinates
    ) -> List[ProjectPactumWorker]:
        """
        Determines proper ranks for worker processes. The rank assignment
        is done according to the following algorithm:
        1. Each agent writes its configuration(group_rank, group_world_size
           , num_workers) to the common store.
        2. Each agent retrieves configuration for all agents
           and performs two level sort using role and rank.
        3. Determine the global rank: the global rank of the workers for the current
           agent is the offset of the infos array up to group_rank of the agent.
           The offset is computed as a sum of local_world_size of all agents that
           have rank less than the group_rank. The workers would have the ranks:
           [offset, offset+local_world_size)
        4. Determine the role rank: The role rank is determined using the algorithms
           in the point 3 with the exception that the offset is done from the first
           agent that has the same role as current one and has the minimum group rank.
        """

        role_infos = self._share_and_gather(store, group_rank, group_world_size, spec)

        my_role_info = role_infos[group_rank]
        worker_world_size, worker_global_ranks = self._get_ranks(role_infos, group_rank)

        role_infos = sorted(
            role_infos, key=functools.cmp_to_key(_RoleInstanceInfo.compare)
        )

        role_start_idx, role_end_idx = _RoleInstanceInfo.find_role_boundaries(
            role_infos, my_role_info.role
        )

        role_pos = next(
            idx
            for idx, role_info in enumerate(role_infos)
            if _RoleInstanceInfo.compare(role_info, my_role_info) == 0
        )

        role_world_size, role_ranks = self._get_ranks(
            role_infos, role_pos, role_start_idx, role_end_idx + 1
        )

        workers = []

        for ind in range(spec.local_world_size):
            worker = ProjectPactumWorker(
                local_rank=ind,
                global_rank=worker_global_ranks[ind],
                role_rank=role_ranks[ind],
                world_size=worker_world_size,
                role_world_size=role_world_size,
                num_pipelines=num_pipelines,
                num_stages=num_stages,
                coordinates=coordinates,
            )
            workers.append(worker)
        return workers

    def _monitor_workers(self, worker_group) -> RunResult:
        role = worker_group.spec.role
        worker_pids = {w.id for w in worker_group.workers}
        assert self._pcontext is not None
        pc_pids = set(self._pcontext.pids().values())
        if worker_pids != pc_pids:
            log.error(
                f"[{role}] worker pids do not match process_context pids."
                f" Expected: {worker_pids}, actual: {pc_pids}"
            )
            return RunResult(state=WorkerState.UNKNOWN)

        result = self._pcontext.wait(0)
        if result:
            if result.is_failed():
                log.error(f"[{role}] Worker group failed")
                # map local rank failure to global rank
                worker_failures = {}
                for local_rank, failure in result.failures.items():
                    worker = worker_group.workers[local_rank]
                    worker_failures[worker.global_rank] = failure

                return RunResult(
                    state=WorkerState.FAILED,
                    failures=worker_failures,
                )
            else:
                # copy ret_val_queue into a map with a global ranks
                workers_ret_vals = {}
                for local_rank, ret_val in result.return_values.items():
                    worker = worker_group.workers[local_rank]
                    workers_ret_vals[worker.global_rank] = ret_val
                return RunResult(
                    state=WorkerState.SUCCEEDED,
                    return_values=workers_ret_vals,
                )
        else:
            return RunResult(state=WorkerState.HEALTHY)

    def _start_workers(self, worker_group) -> Dict[int, Any]:
        spec = worker_group.spec
        store = worker_group.store
        assert store is not None
        master_addr, master_port = super()._get_master_addr_port(store)
        restart_count = spec.max_restarts - self._remaining_restarts

        use_agent_store = spec.rdzv_handler.get_backend() == "static"

        args: Dict[int, Tuple] = {}
        envs: Dict[int, Dict[str, str]] = {}
        for worker in worker_group.workers:
            local_rank = worker.local_rank
            worker_env = {
                "LOCAL_RANK": str(local_rank),
                "RANK": str(worker.global_rank),
                "GROUP_RANK": str(worker_group.group_rank),
                "ROLE_RANK": str(worker.role_rank),
                "ROLE_NAME": spec.role,
                "LOCAL_WORLD_SIZE": str(spec.local_world_size),
                "WORLD_SIZE": str(worker.world_size),
                "GROUP_WORLD_SIZE": str(worker_group.group_world_size),
                "ROLE_WORLD_SIZE": str(worker.role_world_size),
                "MASTER_ADDR": master_addr,
                "MASTER_PORT": str(master_port),
                "TORCHELASTIC_RESTART_COUNT": str(restart_count),
                "TORCHELASTIC_MAX_RESTARTS": str(spec.max_restarts),
                "TORCHELASTIC_RUN_ID": spec.rdzv_handler.get_run_id(),
                "TORCHELASTIC_USE_AGENT_STORE": str(use_agent_store),
                "NCCL_ASYNC_ERROR_HANDLING": str(1),
                "PROJECT_PACTUM_NUM_PIPELINES": str(worker.num_pipelines),
                "PROJECT_PACTUM_NUM_STAGES": str(worker.num_stages),
                "PROJECT_PACTUM_COORDINATES": json.dumps(worker.coordinates),
            }
            if "OMP_NUM_THREADS" in os.environ:
                worker_env["OMP_NUM_THREADS"] = os.environ["OMP_NUM_THREADS"]
            if self._extra_env:
                worker_env.update(self._extra_env)
            envs[local_rank] = worker_env
            worker_args = list(spec.args)
            worker_args = macros.substitute(worker_args, str(local_rank))
            args[local_rank] = tuple(worker_args)

        # scaling events do not count towards restarts (gets same attempt #)
        # remove existing log dir if this restart is due to a scaling event
        attempt_log_dir = os.path.join(self._log_dir, f"attempt_{restart_count}")
        shutil.rmtree(attempt_log_dir, ignore_errors=True)
        os.makedirs(attempt_log_dir)

        assert spec.entrypoint is not None
        self._pcontext = start_processes(
            name=spec.role,
            entrypoint=spec.entrypoint,
            args=args,
            envs=envs,
            log_dir=attempt_log_dir,
            start_method=self._start_method,
            redirects=spec.redirects,
            tee=spec.tee,
        )
        
        # Register the SIGTERM (15) signal to kill the workers
        signal.signal(signal.SIGTERM, self._drain_preempting_workers)

        return self._pcontext.pids()

    def _stop_workers(self, worker_group) -> None:
        self._shutdown()

    def _shutdown(self) -> None:
        if self._pcontext:
            self._pcontext.close()
