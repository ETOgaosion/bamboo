
from simulation_oobleck.simulator import Simulator
import math
import csv
import statistics

class MySimulator(Simulator):
    def __init__(self, seed=None, start_hour=None,
                 model='GPT-3', model_size='350M', spot_instance_trace='traces/p3-trace-16.csv', generate_addition_probabilities=False, removal_probability=None, generate_graphs=False):
        super().__init__(seed, start_hour, model, model_size, spot_instance_trace, generate_addition_probabilities, removal_probability, generate_graphs)
    
        # Amazon EC2 Tesla T4
        if model == 'GPT-3':
            # the number of nodes that can be added at a time, bamboo do lazy reconfigure, not reconfig every time
            if model_size == '350M':
                self.global_batch_size = 1024
            else:
                self.global_batch_size = 2048
        
        # prepare for first time launch
        self.preparation_delta = 10000
        self.check_pt_steps = 10000

        # on demand instance config, no need to change
        def calculate_avg_nodes(file):
            seconds, operations, nodes, nodes_samples = [], [], [], []
            if file.endswith(".csv"):
                with open(file, newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        seconds.append(int(row[0]))
                        operations.append(row[1])
                        nodes.append(row[2])
            current_nodes = 0
            seconds_norepeat = []
            for i in range(0, len(seconds)):
                if len(seconds_norepeat) > 0 and seconds_norepeat[-1] != seconds[i]:
                    nodes_samples.append(current_nodes)
                    seconds_norepeat.append(seconds[i])
                if operations[i] == 'add':
                    current_nodes += 1
                elif operations[i] == 'remove':
                    current_nodes -= 1
                if len(seconds_norepeat) == 0:
                    seconds_norepeat.append(seconds[i])
            nodes_samples.append(current_nodes)
            return statistics.mean(nodes_samples)
    
        self.on_demand_num_instances = math.ceil(calculate_avg_nodes(spot_instance_trace))
        
        self.on_demand_cost = self.on_demand_num_instances * self.on_demand_cost_per_hour
        self.on_demand_performance = (self.global_batch_size * self.on_demand_num_instances) / self.simulate_iteration_delta_calc(self.on_demand_num_instances)
        self.on_demand_value = self.on_demand_performance / self.on_demand_cost

    def reconfigure_delta(self) -> int:
        # reconfigure time (ms)
        reconfigure_map = {
            "350M": {
                8: 13560,
                9: 12853,
                10: 12853,
                11: 12261,
                12: 12261,
                13: 11845,
                14: 11845,
                15: 7157,
                16: 7157,
                17: 6456,
                18: 6456,
                19: 7097,
                20: 7097,
                21: 8369,
                22: 8369,
                23: 6775,
            },
            "1.3B": {
                8: 21437,
                9: 18823,
                10: 18823,
                11: 14644,
                12: 14644,
                13: 13595,
                14: 13595,
                15: 11677,
                16: 11677,
                17: 14639,
                18: 14639,
                19: 13272,
                20: 13272,
                21: 15358,
                22: 15358,
                23: 11163,
            
            },
            "2.7B" : {
                8: 48853, # 理论上pipeline已经不够了
                9: 48853,
                10: 48853,
                11: 53819,
                12: 53819,
                13: 57064,
                14: 57064,
                15: 34481,
                16: 34481,
                17: 46844,
                18: 46844,
                19: 33269,
                20: 33269,
                21: 33307,
                22: 33307,
                23: 24792,
            }
        }

        curr_active_instances = self.active_spot_instances()
        # print(f"last: {self.last_active_instances}, curr: {curr_active_instances}")
        if curr_active_instances < 8:
            curr_active_instances = 8
        if curr_active_instances > 23:
            curr_active_instances = 23
        reconfigure_time = reconfigure_map[self.model_size][curr_active_instances]
        self.last_active_instances = curr_active_instances
        return reconfigure_time

    def fallback_slowdown(self) -> int:
        # nodes fail and slowdown ration, seems a garbage design
        return 1

    def simulate_iteration_delta(self):
        curr_active_instances = self.active_spot_instances()
        # iteration time
        self.iteration_delta = self.simulate_iteration_delta_calc(curr_active_instances)


    def simulate_iteration_delta_calc(self, nodes_num) -> int:
        
        '''
        Returns:
            the iteration time (ms)
        '''
        iteration_map = {
            "350M": {
                8: 27120,
                9: 27120,
                10: 25706,
                11: 25706,
                12: 24522,
                13: 24522,
                14: 23690,
                15: 23690,
                16: 14315,
                17: 14315,
                18: 12913,
                19: 12913,
                20: 14195,
                21: 14195,
                22: 16739,
                23: 16739,
                24: 13550
            },
             "1.3B": {
                8: 42115,
                9: 42115,
                10: 36645,
                11: 36645,
                12: 27660,
                13: 27660,
                14: 24724,
                15: 24724,
                16: 22230,
                17: 22230,
                18: 20053,
                19: 20053,
                20: 22045,
                21: 22045,
                22: 25995,
                23: 25995,
                24: 21047,
             },
            "2.7B": {
                8: 89982,
                9: 89982,
                10: 92425,
                11: 92425,
                12: 10601,
                13: 10601,
                14: 11278,
                15: 11278,
                16: 66840,
                17: 66840,
                18: 75342,
                19: 75342,
                20: 61185,
                21: 61185,
                22: 58904,
                23: 58904,
                24: 47650,
            }

        }
        return iteration_map[self.model_size][nodes_num]
        