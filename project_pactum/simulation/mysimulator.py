
from project_pactum.simulation.simulator import Simulator
from test.bambootest.lab_res_parser import *

class TeslaT4Simulator(Simulator):
    def __init__(self, seed=None, start_hour=None,
                 model='GPT-2', spot_instance_trace=None, generate_addition_probabilities=False, removal_probability=None, generate_graphs=False):
        super().__init__(seed, start_hour, model, spot_instance_trace, generate_addition_probabilities, removal_probability, generate_graphs)
        self.rdzv_model, self.fall_back_model, self.pipeline_delta_model = res_parser_init()
    
        # Amazon EC2 Tesla T4
        if model == 'GPT-2':
            self.samples_per_step = 96
            self.steps_per_run = 188_828
            self.spot_instance_desired_capacity = 48
            self.simulate_step_delta_cache = [8100]
            self.num_stages_target = 2
            self.on_demand_num_instances = 32
            self.on_demand_cost = self.on_demand_num_instances * self.on_demand_cost_per_hour
            self.on_demand_performance = self.samples_per_step / (self.simulate_step_delta_calc(self.on_demand_num_instances // self.num_stages_target) / 1000)
            self.on_demand_value = self.on_demand_performance / self.on_demand_cost
    

    def global_rendezvous_timeout_delta(self):
        # return 6004.3633 * self.num_pipelines + 75630
        return self.rdzv_model.predict(sm.add_constant(np.array([0, self.num_pipelines]))).item(1)
    
    def fallback_slowdown(self):
        # return 2.4297 / (self.num_pipelines * self.num_stages) + 1
        return self.fall_back_model.predict(np.ones(1)/np.array([self.num_pipelines * self.num_stages])).item(0) + 1

    def simulate_step_delta(self):
        self.step_delta = self.simulate_step_delta_calc(self.num_pipelines)
    
    def simulate_step_delta_calc(self, num_pipelines):
        if num_pipelines > len(self.simulate_step_delta_cache):
            for i in range(len(self.simulate_step_delta_cache), num_pipelines):
                self.simulate_step_delta_cache.append(
                    # self.simulate_step_delta_cache[-1] / (0.6891 / (i + 1) + 1)
                    self.simulate_step_delta_cache[-1] / (self.pipeline_delta_model.predict((np.ones(1)/np.array([i + 1]))).item(0) + 1)
                )
        return self.simulate_step_delta_cache[num_pipelines - 1]