
from project_pactum.simulation.simulator import Simulator
from test.bambootest.lab_res_parser import *
from tools.trace16_constructor import calculate_avg_nodes
import math

class MySimulator(Simulator):
    def __init__(self, seed=None, start_hour=None,
                 model='GPT-3', spot_instance_trace='traces/p3-trace-16.csv', generate_addition_probabilities=False, removal_probability=None, generate_graphs=False):
        super().__init__(seed, start_hour, model, spot_instance_trace, generate_addition_probabilities, removal_probability, generate_graphs)
    
        # Amazon EC2 Tesla T4
        if model == 'GPT-3':
            self.start_nodes_num = 8
            self.pipeline_parallel_size_target = 2
            self.global_batch_size = 1024
            self.on_demand_num_instances = int(math.pow(2, math.ceil(math.log2(calculate_avg_nodes(spot_instance_trace)))))
            self.on_demand_cost = self.on_demand_num_instances * self.on_demand_cost_per_hour
            self.on_demand_performance = (self.global_batch_size * self.on_demand_num_instances) / self.simulate_step_delta_calc(self.on_demand_num_instances)
            self.on_demand_value = self.on_demand_performance / self.on_demand_cost
            
        self.preparation_delta = 63000

    def transfer_layer_delta(self):
        return 46.8
        # return 6004.3633 * self.data_parallel_size + 75630
        return self.rdzv_model.predict(sm.add_constant(np.array([0, self.data_parallel_size]))).item(1)

    def fallback_slowdown(self):
        return self.pipeline_parallel_size / (self.pipeline_parallel_size - 1)

    def simulate_step_delta(self):
        self.step_delta = self.simulate_step_delta_calc(self.data_parallel_size * self.pipeline_parallel_size)
    
    def simulate_step_delta_calc(self, nodes_num):
        data = {
            8: 19.1,
            10: 27.3,
            12: 17.6,
            14: 22.3,
            16: 14.7
        }
        if data.get(nodes_num) is not None:
            return data[nodes_num]
        else:
            return data[int(math.pow(2, math.ceil(math.log2(nodes_num))))]