import csv
import dataclasses
import datetime
import enum
import heapq
import logging
import math
import random
import statistics
import typing
import matplotlib.pyplot as plt
from pathlib import Path

from simulation.utils import *

logger = logging.getLogger(__name__)

class EventKind(enum.IntEnum):
    SPOT_INSTANCE_ADD = 1
    SPOT_INSTANCE_REMOVE = 2
    SPOT_INSTANCE_GENERATE = 3
    SPOT_INSTANCE_READY = 4
    PREPARATION = 5
    RECONFIGURE = 6
    TRAINING_STEP_COMPLETE = 7

@dataclasses.dataclass(order=True)
class Event:
    delta: float
    kind: EventKind
    data: typing.Dict = dataclasses.field(compare=False)

class SystemStatus(enum.Enum):
    STOPPED = enum.auto()
    RENDEZVOUS = enum.auto()
    RUNNING = enum.auto()

class NodeStatus(enum.Enum):
    CREATING = enum.auto()
    READY = enum.auto()
    RUNNING = enum.auto()

@dataclasses.dataclass
class Result:
    removal_probability: float
    preemption_mean: float
    preemption_median: float
    preemption_stdev: float
    lifetime_mean: float
    lifetime_median: float
    lifetime_stdev: float
    num_preemptions: int
    num_fatal_failures: int
    num_iterations_complete: int
    average_instances: float
    average_performance: float
    average_cost: float
    average_value: float

class SpotInstance:
    def __init__(self, name, start):
        self.name = name
        self.start = start
        self.status = NodeStatus.CREATING
        self.global_id = None
        self.active_coordinates = []
        self.previous_coordinates = []

    def is_creating(self):
        return self.status == NodeStatus.CREATING

    def set_ready(self):
        self.status = NodeStatus.READY

    def is_ready(self):
        return self.status == NodeStatus.READY

    def set_running(self):
        self.status = NodeStatus.RUNNING

    def is_running(self):
        return self.status == NodeStatus.RUNNING

    def uptime(self, end):
        return end - self.start

    def __str__(self):
        return self.name

class Simulator:

    def __init__(self,
                 seed=None,
                 start_hour=None,
                 model='GPT-2',
                 spot_instance_trace=None,
                 generate_addition_probabilities=False,
                 removal_probability=None,
                 generate_graphs=False):
        if spot_instance_trace is not None:
            self.spot_instance_trace = open(spot_instance_trace, 'r')
        else:
            self.spot_instance_trace = None
        self.generate_graphs = generate_graphs

        self.seed = seed
        if self.seed is not None:
            self.r = random.Random(self.seed)
            logger.info(f'Using seed: {self.seed}')
        else:
            self.r = random.Random()
        self.generate_addition_probabilities = generate_addition_probabilities
        self.removal_probability = removal_probability

        self.hour = datetime.timedelta(hours=1)
        self.second = datetime.timedelta(seconds=1)
        self.millisecond = datetime.timedelta(milliseconds=1)
        self.milliseconds_per_second = self.second / self.millisecond
        self.milliseconds_per_hour = self.hour / self.millisecond

        self.spot_instance_name_format = 'node{id}'
        self.spot_instance_next_id = 1
        if not generate_addition_probabilities:
            self.spot_instance_addition_probability = {
                0: 0.05,
                1: 0.05,
                2: 0.05,
                3: 0.50,
                4: 0.50,
                5: 0.50,
                6: 0.05,
                7: 0.05,
                8: 0.05,
                9: 0.05,
                10: 0.05,
                11: 0.05,
                12: 0.05,
                13: 0.05,
                14: 0.05,
                15: 0.00,
                16: 0.00,
                17: 0.00,
                18: 0.00,
                19: 0.00,
                20: 0.00,
                21: 0.00,
                22: 0.00,
                23: 0.05,
            }
        else:
            self.spot_instance_addition_probability = self.generate_probabilities()
        if removal_probability is None:
            self.spot_instance_removal_probability = {
                0: 0.05,
                1: 0.05,
                2: 0.05,
                3: 0.01,
                4: 0.01,
                5: 0.01,
                6: 0.05,
                7: 0.05,
                8: 0.05,
                9: 0.05,
                10: 0.05,
                11: 0.05,
                12: 0.05,
                13: 0.05,
                14: 0.05,
                15: 0.25,
                16: 0.25,
                17: 0.25,
                18: 0.25,
                19: 0.25,
                20: 0.25,
                21: 0.25,
                22: 0.25,
                23: 0.05,
            }
        else:
            self.spot_instance_removal_probability = {}
            for hour in range(24):
                self.spot_instance_removal_probability[hour] = removal_probability

        self.start_hour = start_hour
        # I do not understand why we need this
        self.spot_instance_creation_time = 45_000 # milliseconds
        self.preparation_delta = 30_000 # milliseconds

        self.spot_instances = {}
        self.rendezvous_version = 0
        self.rendezvous = []
        self.num_workers_waiting = 0
        self.data_parallel_size = 0
        self.pipeline_parallel_size = 0

        self.num_iterations_complete = 0
        self.num_fatal_failures = 0
        self.num_spot_instance_removals = 0

        # self.fallback_slowdown = 1.5
        self.fallback_event = None
        self.fallback_handled = False

        self.spot_instance_removal_times = []
        self.spot_instance_lifetimes = []

        self.start_delta = None
        self.previous_iteration_execute_delta = 0

        self.events = []
        heapq.heapify(self.events)

        self.status = SystemStatus.STOPPED

        self.on_demand_cost_per_hour = 3.06
        self.spot_instance_cost_per_hour = 0.91

        self.model = model

    def generate_probabilities(self):
        probability = {}
        for hour in range(24):
            probability[hour] = self.r.random()
        return probability

    # implement by child
    
    def reconfigure_delta(self):
        return 0
    
    # implement by child
    def fallback_slowdown(self):
        return 0

    # implement by child
    def simulate_iteration_delta(self):
        pass

    def info(self, delta, message):
        print(f'[{delta/1000.0:.3f}] {message}')
 
    def get_spot_instance_next_name(self):
        name = self.spot_instance_name_format.format(
            id=self.spot_instance_next_id
        )
        self.spot_instance_next_id += 1
        return name

    def generate_spot_instance_probability_delta(self,
                                                 current_time,
                                                 current_delta,
                                                 probability):
        hour = current_time.hour
        p = probability[hour]
        if p > self.r.random():
            local_delta = datetime.timedelta(seconds=self.r.randrange(0, 3600))
            delta = current_delta + local_delta
            return delta
        return None

    def generate_spot_instance_addition_delta(self,
                                              current_time,
                                              current_delta):
        return self.generate_spot_instance_probability_delta(
            current_time,
            current_delta,
            self.spot_instance_addition_probability
        )

    def generate_spot_instance_removal_delta(self,
                                             current_time,
                                             current_delta):
        return self.generate_spot_instance_probability_delta(
            current_time,
            current_delta,
            self.spot_instance_removal_probability
        )

    def create_event(self, delta, kind, data):
        if isinstance(delta, datetime.timedelta):
            event = Event(delta // self.millisecond, kind, data)
        else:
            event = Event(delta, kind, data)
        heapq.heappush(self.events, event)
        return event

    def create_spot_instance_generate_event(self, delta):
        return self.create_event(delta, EventKind.SPOT_INSTANCE_GENERATE, {})

    def create_spot_instance_add_event(self, delta, name=None):
        if name is None:
           name = self.get_spot_instance_next_name()
        return self.create_event(delta, EventKind.SPOT_INSTANCE_ADD, {
            'name': name,
        })
    def create_spot_instance_remove_event(self, delta, name):
        return self.create_event(delta, EventKind.SPOT_INSTANCE_REMOVE, {
            'name': name,
        })

    def create_spot_instance_ready_event(self, delta, name):
        return self.create_event(delta, EventKind.SPOT_INSTANCE_READY, {
            'name': name,
        })

    def create_preparation_event(self, delta):
        return self.create_event(
            delta + self.preparation_delta,
            EventKind.PREPARATION,
            {}
        )
    
    def create_reconfigure_event(self, delta):
        return self.create_event(
            delta + self.reconfigure_delta(),
            EventKind.RECONFIGURE,
            {}
        )

    def create_training_iteration_execute_event(self, delta, rendezvous_version):
        return self.create_event(
            delta + self.iteration_delta,
            EventKind.TRAINING_STEP_COMPLETE,
            {'rendezvous_version': rendezvous_version}
        )

    def create_training_iteration_execute_event_absolute(self, delta,
                                                     rendezvous_version):
        return self.create_event(
            delta,
            EventKind.TRAINING_STEP_COMPLETE,
            {'rendezvous_version': rendezvous_version}
        )

    def generate_spot_instance_initial_events(self, start):
        # Generate the initial instances
        spot_instance_initial_probability = self.spot_instance_addition_probability[start.hour]
        delta = 0
        for i in range(self.spot_instance_desired_capacity):
            if spot_instance_initial_probability > self.r.random():
                event = self.create_spot_instance_add_event(delta)
        self.create_spot_instance_generate_event(delta)

    # def generate_spot_instance_events(self, start, duration): # TODO
    def generate_spot_instance_events(self, start, delta):
        self.info(delta, f'generate_spot_instance_events {delta}')
        current_delta = delta * self.millisecond
        self.create_spot_instance_generate_event(current_delta + self.hour)

        current_instances = {}
        for name, instance in self.spot_instances.items():
            current_instances[name] = current_delta

        # The remaining code generates add and remove events for the next hour
        current_time = start + current_delta

        # Run removal for currently running nodes
        removed_instances = []
        for name in current_instances.keys():
            delta = self.generate_spot_instance_removal_delta(current_time,
                                                              current_delta)
            if delta is None:
                continue
            removed_instances.append((delta, name))
        heapq.heapify(removed_instances)

        # Run additions for the maximum number of instances you ever need
        # this hour
        possible_added_deltas = []
        requested_capacity = self.spot_instance_desired_capacity - len(current_instances) + len(removed_instances)
        for _ in range(requested_capacity):
            delta = self.generate_spot_instance_addition_delta(current_time, current_delta)
            if delta is None:
                continue
            possible_added_deltas.append(delta)
        heapq.heapify(possible_added_deltas)

        # Check if we have to throw out any additions because we're already
        # at capacity
        while len(removed_instances) > 0 or len(possible_added_deltas) > 0:
            # The next event is a removal, so just do it
            if len(removed_instances) > 0 and (len(possible_added_deltas) == 0 or removed_instances[0][0] < possible_added_deltas[0]):
                delta, name = heapq.heappop(removed_instances)

                event = self.create_spot_instance_remove_event(delta, name)

                del current_instances[name]
            # The next event is an addition, only do it if we're under
            # desired capacity
            else:
                delta = heapq.heappop(possible_added_deltas)

                # Skip this addition
                if len(current_instances) == self.spot_instance_desired_capacity:
                    continue

                event = self.create_spot_instance_add_event(delta)

                name = event.data['name']
                current_instances[name] = delta

                # Check if we also attempt to remove this new instance in
                # this hour
                delta = self.generate_spot_instance_removal_delta(
                    current_time,
                    current_delta
                )
                if delta is None or delta < current_instances[name]:
                    continue
                heapq.heappush(removed_instances, (delta, name))

    # def append_value(self, delta):
    #     if len(self.performance_ys) == 0 or len(self.cost_ys) == 0:
    #         return
    #     if self.cost_ys[-1] == 0.0:
    #         self.value_xs.append(delta / self.milliseconds_per_hour)
    #         self.value_ys.append(0)
    #         return

    #     self.value_xs.append(delta / self.milliseconds_per_hour)
    #     self.value_ys.append(
    #         self.performance_ys[-1] / self.cost_ys[-1]
    #     )

    def simulate_spot_instance_add(self, delta, data):
        self.info(delta, f'{data["name"]} simulate_spot_instance_add: {delta}')
        name = data['name']
        self.spot_instances[name] = SpotInstance(name, delta)
        self.create_spot_instance_ready_event(
            delta + self.spot_instance_creation_time,
            name,
        )

    def simulate_fatal_failure(self, delta, name, data):
        self.info(delta, f'{data["name"]} simulate_fatal_failure: {delta}')
        self.info(
            delta,
            f'{name} caused a fatal failure, starting global rendezvous'
        )
        self.num_fatal_failures += 1
        self.simulate_rendezvous_start(delta, True)

    def simulate_spot_instance_remove(self, delta, data):
        self.info(delta, f'{data["name"]} simulate_spot_instance_remove: {delta}')
        name = data['name']
        instance = self.spot_instances[name]

        self.num_spot_instance_removals += 1
        self.spot_instance_lifetimes.append(delta - instance.start)
        self.spot_instance_removal_times.append(delta)
        del self.spot_instances[name]

        if instance.is_running():
            # This is a fatal failure
            if len(instance.active_coordinates) > 1:
                self.simulate_fatal_failure(delta, name, data)
                return

            coordinates = instance.active_coordinates[0]
            # Find which node has my redundant coordinates
            search = (coordinates[0], coordinates[1] - 1)
            if search[1] == -1:
                search = (search[0], self.pipeline_parallel_size - 1)
            for n, i in self.spot_instances.items():
                found = False
                for c in i.active_coordinates:
                    if c == search:
                        # This node recovered previously, so it doesn't have
                        # the redundant coordinates
                        if len(i.active_coordinates) > 1:
                            self.simulate_fatal_failure(delta, name)
                            return
                        i.active_coordinates.append(coordinates)
                        found = True
                        break
                if found:
                    break
        
        # Re-simulate the iteration delta now that we lost a node
        if self.status == SystemStatus.RUNNING:
            if self.fallback_event is None:
                self.fallback_event = (self.num_iterations_complete, delta)
                self.fallback_handled = False
                self.iteration_delta = int(self.iteration_delta * self.fallback_slowdown()) # Fucking strange

    def simulate_rendezvous_start(self, delta, isGlobal):
        self.info(delta, f'simulate_rendezvous_start: {delta}')
        self.status = SystemStatus.RENDEZVOUS
        self.simulate_rendezvous_restart(delta)
        if isGlobal:
            self.create_preparation_event(delta)
        else:
            self.create_reconfigure_event(delta)

    def simulate_rendezvous_restart(self, delta):
        self.info(delta, f'simulate_rendezvous_restart: {delta}')
        assert self.status == SystemStatus.RENDEZVOUS
        self.rendezvous = []
        for name, instance, in self.spot_instances.items():
            if instance.is_ready() or instance.is_running():
                self.rendezvous.append(name)

    def simulate_preparation_common(self, delta):
        self.info(delta, f'simulate_preparation: {delta}')
        for i, name in enumerate(self.rendezvous):
            if name not in self.spot_instances:
                self.info(
                    delta,
                    f'{name} terminated during redezvous, restarting'
                )
                self.simulate_rendezvous_restart(delta)
                self.create_preparation_event(delta)
                return
            instance = self.spot_instances[name]
            instance.global_id = i
        self.simulate_assign_coordinates(delta)
        self.fallback_event = None
        self.fallback_handled = False
        self.rendezvous_version += 1
        self.info(
            delta,
            f'{len(self.rendezvous)} nodes completed rendezvous version '
            f'{self.rendezvous_version}, '
            f'{self.data_parallel_size}x{self.pipeline_parallel_size} configuration'
        )
        self.rendezvous = []
        if self.data_parallel_size != 0:
            self.status = SystemStatus.RUNNING
            self.simulate_iteration_delta()
            self.create_training_iteration_execute_event(delta,
                                                     self.rendezvous_version)
            if self.start_delta is None:
                self.start_delta = delta
                self.previous_iteration_execute_delta = self.start_delta
        else:
            self.status = SystemStatus.STOPPED

    def simulate_spot_instance_ready(self, delta, data):
        self.info(delta, f'{data["name"]} simulate_spot_instance_ready: {delta}')
        name = data['name']

        # This node has already been removed
        if name not in self.spot_instances:
            return

        instance = self.spot_instances[name]
        instance.set_ready()

        if self.status == SystemStatus.STOPPED:
            if len(self.spot_instances) < self.start_nodes_num:
                return
            self.info(delta, f'{name} starting global rendezvous')
            self.simulate_rendezvous_start(delta, True)
        elif self.status == SystemStatus.RENDEZVOUS:
            self.rendezvous.append(name)
        elif self.status == SystemStatus.RUNNING:
            self.num_workers_waiting += 1

    def simulate_preparation(self, delta):
        self.info(delta, f'simulate_preparation: {delta}')
        self.simulate_preparation_common(delta)

    def simulate_reconfigure(self, delta):
        self.info(delta, f'simulate_reconfigure: {delta}')
        self.simulate_preparation_common(delta)

    def simulate_assign_coordinates(self, delta):
        self.info(delta, f'simulate_assign_coordinates')
        if len(self.rendezvous) < self.pipeline_parallel_size_target:
            data_parallel_size = 0
            pipeline_parallel_size = 0
        else:
            pipeline_parallel_size = self.pipeline_parallel_size_target
            data_parallel_size = len(self.rendezvous) // pipeline_parallel_size
        num_workers_waiting = 0

        previous_data_parallel_size = self.data_parallel_size
        previous_pipeline_parallel_size = self.pipeline_parallel_size

        required_coordinates = []
        for i in range(data_parallel_size):
            for j in range(pipeline_parallel_size):
                required_coordinates.append((i, j))

        for name in self.rendezvous:
            instance = self.spot_instances[name]
            assert instance.is_ready() or instance.is_running()
            instance.previous_coordinates = instance.active_coordinates
            try:
                coordinates = required_coordinates.pop(0)
                instance.active_coordinates = [coordinates]
                instance.set_running()
            except IndexError:
                instance.active_coordinates = []
                instance.set_ready()
                num_workers_waiting += 1

        self.data_parallel_size = data_parallel_size
        self.pipeline_parallel_size = pipeline_parallel_size
        self.num_workers_waiting = num_workers_waiting

    def get_num_workers_overloaded(self):
        num_workers_overloaded = 0
        for name, instance in self.spot_instances.items():
            if not instance.is_running():
                continue
            elif len(instance.active_coordinates) > 1:
                assert len(instance.active_coordinates) == 2
                num_workers_overloaded += 1
        return num_workers_overloaded

    def simulate_should_reconfigure(self):
        num_workers_overloaded = self.get_num_workers_overloaded()
        num_workers_waiting = self.num_workers_waiting

        # If we can easily re-balance, do it
        if num_workers_overloaded > 0 and num_workers_waiting >= num_workers_overloaded:
            return True

        num_original_workers = self.data_parallel_size * self.pipeline_parallel_size
        num_active_workers = num_original_workers - num_workers_overloaded

        # If we're above a 5% chance of failure, re-configure/re-balance
        # I cannot remove an overloaded node, or the node that now has no
        # redundancy
        if num_workers_overloaded > 0 and (2 * num_workers_overloaded / num_active_workers) > 0.05:
            return True

        # If we can add another pipeline, do it
        potential_data_parallel_size = (num_active_workers + num_workers_waiting) // self.pipeline_parallel_size_target
        if potential_data_parallel_size > self.data_parallel_size:
            return True

        return False

    def simulate_training_iteration_execute(self, delta, data):
        rendezvous_version = data['rendezvous_version']
        if rendezvous_version != self.rendezvous_version:
            return

        # Handle fallback events
        if self.fallback_event is not None:
            event_num_iterations_complete, event_delta = self.fallback_event
            if not self.fallback_handled and event_num_iterations_complete == self.num_iterations_complete:
                # The duration we need to add to handle the fallback
                d = int((delta - event_delta) * (self.fallback_slowdown() - 1.0))
                self.create_training_iteration_execute_event_absolute(
                    d + delta,
                    rendezvous_version
                )
                self.fallback_handled = True
                return

        self.num_iterations_complete += 1

        # Calculate performance
        iteration_duration = delta - self.previous_iteration_execute_delta # milliseconds
        #print('Step duration:', iteration_duration)
        iteration_duration_seconds = iteration_duration / self.milliseconds_per_second
        iteration_duration_hours = iteration_duration / self.milliseconds_per_hour
        #print('Step duration (s):', iteration_duration_seconds)
        samples_per_second = (self.global_batch_size * self.data_parallel_size * self.pipeline_parallel_size) / iteration_duration_seconds


        previous_delta_hours = self.previous_iteration_execute_delta / self.milliseconds_per_hour
        delta_hours = delta / self.milliseconds_per_hour
        self.performance_xs.append(previous_delta_hours)
        self.performance_ys.append(samples_per_second)
        self.performance_xs.append(delta_hours)
        self.performance_ys.append(samples_per_second)

        
        current_cost_per_hour = self.cost_ys[-1]
        current_cost_delta = delta_hours
        total_cost = 0.0
        #print('Previous delta hours:', previous_delta_hours)
        #print('Delta hours:', delta_hours)
        #print('Duration (s):', iteration_duration_hours)
        #print(self.cost_xs, self.cost_ys)
        #print('Finding the cost...', current_cost_per_hour)
        i = -1
        while True:
            x1 = self.cost_xs[i]
            y1 = self.cost_ys[i]
            try:
                x2 = self.cost_xs[i-1]
                y2 = self.cost_ys[i-1]
            except IndexError:
                total_cost += current_cost_per_hour * (current_cost_delta - previous_delta_hours)
                break
            assert x1 == x2

            if x1 > previous_delta_hours:
                total_cost += current_cost_per_hour * (current_cost_delta - x1)
                current_cost_per_hour = y2
                current_cost_delta = x1
            else:
                total_cost += current_cost_per_hour * (current_cost_delta - previous_delta_hours)
                break
            i -= 2

        average_cost_per_hour = total_cost / iteration_duration_hours
        
        self.value_xs.append(previous_delta_hours)
        self.value_ys.append(samples_per_second / average_cost_per_hour)
        self.value_xs.append(delta_hours)
        self.value_ys.append(samples_per_second / average_cost_per_hour)

            #print('x1 y1 x2 y2', x1,y1,x2,y2)
            #if x1 < previous_delta_hours:
            #    break

        #assert False

        self.previous_iteration_execute_delta = delta

        if self.num_iterations_complete % 10000 == 0:
            self.info(delta, f'{self.num_iterations_complete} iterations complete')
        if self.simulate_should_reconfigure():
            self.info(
                delta,
                f'reconfiguration after iteration {self.num_iterations_complete}'
            )
            self.simulate_rendezvous_start(delta, False)
        else:
            self.create_training_iteration_execute_event(
                delta,
                self.rendezvous_version
            )

    def calculate_average(self, xs, ys, duration):
        previous_x = None
        previous_y = None
        total = 0.0
        for x, y in zip(xs, ys):
            if previous_x is None:
                previous_x = x
                previous_y = y
            else:
                assert previous_y == y
                total += (x - previous_x) * y
                previous_x = None
                previous_y = None
        return total / duration

    def calculate_average_old(self, xs, ys, duration):
        print('=== WARNING OLD')
        previous_x = 0.0
        previous_y = 0.0
        total = 0.0
        for x, y in zip(xs, ys):
            total += (x - previous_x) * previous_y
            previous_x = x
            previous_y = y
        total += (duration - previous_x) * previous_y
        return total / duration
        
    def simulate(self, duration=None, fig_directory="res/simulator"):
        start = datetime.datetime.now(datetime.timezone.utc)
        start = start.replace(minute=0, second=0, microsecond=0)
        if self.start_hour is not None:
            start = start.replace(hour=self.start_hour)

        logger.info(f'Starting at {start}')
        
        delta = 0

        if self.spot_instance_trace is None:
            logger.info(f' Generating spot instance events...')
            self.generate_spot_instance_initial_events(start)
        else:
            reader = csv.reader(self.spot_instance_trace)
            logger.info(f'read {self.spot_instance_trace} reader: {reader.line_num}')
            for row in reader:
                delta_str, event, name = row
                delta = int(delta_str)
                if event == 'add':
                    self.create_spot_instance_add_event(delta, name)
                elif event == 'remove':
                    self.create_spot_instance_remove_event(delta, name)
                else:
                    raise NotImplementedError

        instances_xs = []
        instances_ys = []
        self.performance_xs = []
        self.performance_ys = []
        self.cost_xs = []
        self.cost_ys = []
        self.value_xs = []
        self.value_ys = []
        
        logger.info(f'len(self.events): {len(self.events)}')

        while len(self.events) > 0:
            event = heapq.heappop(self.events)

            kind = event.kind
            delta = event.delta
            data = event.data

            if duration is not None and delta > duration:
                delta = duration
                break

            if kind == EventKind.SPOT_INSTANCE_ADD:
                self.simulate_spot_instance_add(delta, data)
            elif kind == EventKind.SPOT_INSTANCE_REMOVE:
                self.simulate_spot_instance_remove(delta, data)
            elif kind == EventKind.SPOT_INSTANCE_GENERATE:
                self.generate_spot_instance_events(start, delta)
            elif kind == EventKind.SPOT_INSTANCE_READY:
                self.simulate_spot_instance_ready(delta, data)
            elif kind == EventKind.PREPARATION:
                self.simulate_preparation(delta)
            elif kind == EventKind.RECONFIGURE:
                self.simulate_reconfigure(delta)
            elif kind == EventKind.TRAINING_STEP_COMPLETE:
                self.simulate_training_iteration_execute(delta, data)
            else:
                raise ValueError(f'Unknown kind: {kind}')

            # We're done our training
            if duration is None and (hasattr(self, "iterations_per_run") and self.num_iterations_complete == self.iterations_per_run):
                break

            # We still need to process more events for this delta
            next_event = self.events[0] if len(self.events) > 0 else None
            next_delta = next_event.delta if next_event else None
            if delta == next_delta:
                continue

            # Initialize the number of instances and cost
            if len(instances_xs) == 0 and delta > 0:
                num_instances = len(self.spot_instances)
                instances_xs.append(0)
                instances_ys.append(num_instances)
                self.cost_xs.append(0)
                self.cost_ys.append(
                    num_instances * self.spot_instance_cost_per_hour
                )
            elif len(instances_xs) > 0:
                previous_num_instances = instances_ys[-1]
                num_instances = len(self.spot_instances)
                if previous_num_instances != num_instances:
                    delta_hours = delta / self.milliseconds_per_hour
                    instances_xs.append(delta_hours)
                    instances_ys.append(previous_num_instances)
                    self.cost_xs.append(delta_hours)
                    self.cost_ys.append(previous_num_instances * self.spot_instance_cost_per_hour)
                    instances_xs.append(delta_hours)
                    instances_ys.append(num_instances)
                    self.cost_xs.append(delta_hours)
                    self.cost_ys.append(num_instances * self.spot_instance_cost_per_hour)

        duration_hours_whole = math.ceil(delta / self.milliseconds_per_hour)

        duration_hours = self.performance_xs[-1]
        num_instances = len(self.spot_instances)
        instances_xs.append(duration_hours)
        instances_ys.append(num_instances)
        self.cost_xs.append(duration_hours)
        self.cost_ys.append(num_instances * self.spot_instance_cost_per_hour)

        # Complete the remaining
        for name, instance in self.spot_instances.items():
            self.spot_instance_lifetimes.append(
                delta - instance.start
            )

        spot_instance_between_removal_times = []
        previous_removal_time = self.spot_instance_removal_times[0] \
            if len(self.spot_instance_removal_times) > 0 else None
        for removal_time in self.spot_instance_removal_times[1:]:
            spot_instance_between_removal_times.append(
                removal_time - previous_removal_time
            )
            previous_removal_time = removal_time

        performance_value_duration_hours = (duration_hours - (self.start_delta / self.milliseconds_per_hour))

        result = Result(
            removal_probability = self.removal_probability,
            preemption_mean = statistics.mean(spot_instance_between_removal_times) / self.milliseconds_per_hour if len(spot_instance_between_removal_times) > 0 else 0,
            preemption_median = statistics.mean(spot_instance_between_removal_times) / self.milliseconds_per_hour if len(spot_instance_between_removal_times) > 0 else 0,
            preemption_stdev = statistics.stdev(spot_instance_between_removal_times) / self.milliseconds_per_hour if len(spot_instance_between_removal_times) > 1 else 0,
            lifetime_mean = statistics.mean(self.spot_instance_lifetimes) / self.milliseconds_per_hour,
            lifetime_median = statistics.median(self.spot_instance_lifetimes) / self.milliseconds_per_hour,
            lifetime_stdev = statistics.stdev(self.spot_instance_lifetimes) / self.milliseconds_per_hour,
            num_preemptions = self.num_spot_instance_removals,
            num_fatal_failures = self.num_fatal_failures,
            num_iterations_complete = self.num_iterations_complete,
            average_instances = self.calculate_average(instances_xs, instances_ys, duration_hours),
            average_performance = self.calculate_average(self.performance_xs, self.performance_ys, performance_value_duration_hours),
            average_cost = self.calculate_average(self.cost_xs, self.cost_ys, duration_hours),
            average_value = self.calculate_average(self.value_xs, self.value_ys, performance_value_duration_hours),
        )

        if self.generate_graphs:
            #pdf_suffix = f'-seed-{self.seed}-start-hour-{self.start_hour}-generate-addition-probabilities-{self.generate_addition_probabilities}-removal-probability-{self.removal_probability}.pdf'
            pdf_suffix = f'-{self.model}.pdf'
            
    
            Path(fig_directory).mkdir(parents=True, exist_ok=True)

            # Instances graph
            graph(
                'Time (hours)',
                instances_xs,
                duration_hours_whole,
                '# Instances',
                instances_ys,
                max(self.on_demand_num_instances, max(instances_ys)),
                result.average_instances,
                on_demand=self.on_demand_num_instances,
                out=f'{fig_directory}/instances{pdf_suffix}',
            )
            
            print(self.on_demand_performance, max(self.performance_ys), result.average_performance)

            # Performance graph
            graph(
                'Time (hours)',
                self.performance_xs,
                duration_hours_whole,
                'Performance (samples per second)',
                self.performance_ys,
                max(self.on_demand_performance, max(self.performance_ys)),
                result.average_performance,
                on_demand=self.on_demand_performance,
                out=f'{fig_directory}/performance{pdf_suffix}',
            )

            print('Model:', self.model)
            print('  Performance:', 'D', self.on_demand_performance, 'B', result.average_performance)

            # Cost graph
            graph(
                'Time (hours)',
                self.cost_xs,
                duration_hours_whole,
                'Cost ($ per hour)',
                self.cost_ys,
                max(self.on_demand_cost, max(self.cost_ys)),
                result.average_cost,
                on_demand=self.on_demand_cost,
                out=f'{fig_directory}/cost{pdf_suffix}',
            )

            print('  Cost:', 'D', self.on_demand_cost, 'B', result.average_cost)

            # Value graph
            graph(
                'Time (hours)',
                self.value_xs,
                duration_hours_whole,
                'Value (performance per cost)',
                self.value_ys,
                max(self.on_demand_value, max(self.value_ys)),
                result.average_value,
                on_demand=self.on_demand_value,
                out=f'{fig_directory}/value{pdf_suffix}',
            )

            print('  Value:', 'D', self.on_demand_value, 'B', result.average_value)
            
            # ======================== Plot on single graph ========================
            plt.clf()
            params = {
                'legend.fontsize': 'x-small',
                'axes.labelsize': 'x-small',
                'axes.titlesize': 'x-small',
                'xtick.labelsize': 'x-small',
                'ytick.labelsize': 'x-small',
                'figure.figsize': (15.0, 10.0),
            }
            plt.rcParams.update(params)
            
            fig, axs = plt.subplots(4)
            fig.suptitle('Result Comparison')
            plt.tight_layout(pad=1, w_pad=1, h_pad=2)
            
            graph_together(
                axs[0],
                'Time (hours)',
                instances_xs,
                duration_hours_whole,
                '# Instances',
                instances_ys,
                max(self.on_demand_num_instances, max(instances_ys)),
                result.average_instances,
                on_demand=self.on_demand_num_instances
            )

            # Performance graph
            graph_together(
                axs[1],
                'Time (hours)',
                self.performance_xs,
                duration_hours_whole,
                'Performance (samples per second)',
                self.performance_ys,
                max(self.on_demand_performance, max(self.performance_ys)),
                result.average_performance,
                on_demand=self.on_demand_performance
            )
            
            # Cost graph
            graph_together(
                axs[2],
                'Time (hours)',
                self.cost_xs,
                duration_hours_whole,
                'Cost ($ per hour)',
                self.cost_ys,
                max(self.on_demand_cost, max(self.cost_ys)),
                result.average_cost,
                on_demand=self.on_demand_cost
            )

            # Value graph
            graph_together(
                axs[3],
                'Time (hours)',
                self.value_xs,
                duration_hours_whole,
                'Value (performance per cost)',
                self.value_ys,
                max(self.on_demand_value, max(self.value_ys)),
                result.average_value,
                on_demand=self.on_demand_value
            )
            
            plt.savefig(
                f'{fig_directory}/total{pdf_suffix}',
                bbox_inches='tight',
                pad_inches=0.25
            )

        # print('Preemptions')
        # print('  - Mean:', result.preemption_mean, 'hours')
        # print('  - Median:', result.preemption_median, 'hours')
        # print('  - Stdev:', result.preemption_stdev, 'hours')
        # print('Lifetimes')
        # print('  - Mean:', result.lifetime_mean, 'hours')
        # print('  - Median:', result.lifetime_median, 'hours')
        # print('  - Stdev:', result.lifetime_stdev, 'hours')
        # print('Number of preemptions:', result.num_preemptions)
        # print('Number of fatal failures:', result.num_fatal_failures)
        # print('Number of iterations complete:', result.num_iterations_complete)

        self.info(delta, f'Ending after {duration_hours} hours')

        return result
