import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pickle
import os
import dataclasses

results = {}
isinstances_xs = []
isinstances_ys = []
performances_xs = {}
performances_ys = {}

models = ['bamboo', 'nore', 'oobleck', 'varu']
traces = ['g4dn', 'p3']
model_sizes = ['350M', '1.3B', '2.7B', '6.7B']
color = {'bamboo': 'green', 'nore': 'red', 'oobleck': 'purple', 'varu': 'black'}

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

def get_data():
    for model in models:
        for trace in traces:
            for model_size in model_sizes:
                if not os.path.exists(f'data/{model}/{trace}/{model_size}'):
                    continue
                key = model + '-' + trace + '-' + model_size
                results[key] = pickle.load(open(f'data/{model}/results_{trace}_{model_size}.pkl', 'rb'))
                if len(isinstances_xs) == 0:
                    isinstances_xs = pickle.load(open(f'data/{model}/isinstances_xs_{trace}_{model_size}.pkl', 'rb'))
                    isinstances_ys = pickle.load(open(f'data/{model}/isinstances_ys_{trace}_{model_size}.pkl', 'rb'))
                performances_xs[key] = pickle.load(open(f'data/{model}/performances_xs_{trace}_{model_size}.pkl', 'rb'))
                performances_ys[key] = pickle.load(open(f'data/{model}/performances_ys_{trace}_{model_size}.pkl', 'rb'))

def plot_instances(axes):
    axes.plot(isinstances_xs, isinstances_ys, linewidth=0.5, color='blue')
    axes.set_title('Spot Instances Number Over Time')
    axes.set_xlabel('Time (hours)')
    axes.set_ylabel('Instances Number')

def plot_performance_together(axes, model_size):
    for model in models:
        for trace in traces:
            key = model + '-' + trace + '-' + model_size
            if key not in performances_xs:
                continue
            axes.plot(performances_xs[key], performances_ys[key], linewidth=0.5, color=color[model])
            axes.set_title('Thoughput in GPT-3 ' + model_size)
            axes.set_xlabel('Time (hours)')
            axes.set_ylabel('Throughput (samples/s)')

def plot_performance():
    get_data()

    fig, axs = plt.subplots(2, 2, figsize=(15, 10))
    
    plot_instances(axs(0, 0))
    plot_performance_together(axs(0, 1), '350M')
    plot_performance_together(axs(1, 0), '1.3B')
    plot_performance_together(axs(1, 1), '2.7B')
    
    plt.legend(handles=[mpatches.Patch(color=color, label=label) for label, color in color.items()], bbox_to_anchor=(0, 1.02, 1, 0.2), loc="lower left", mode="expand", borderaxespad=0, ncol=4)

    plt.tight_layout()
    plt.savefig('res/performances.png')

    plt.close()

def plot_total_throughputs():
    total_throughputs = {}
    for model in models:
        for trace in traces:
            if total_throughputs[trace] is None:
                total_throughputs[trace] = []
            key = model + '-' + trace + '-' + '350M'
            assert key in results
            total_throughputs[trace].append(results[key].average_performance)
    fig, axs = plt.subplots(1, 2, figsize=(5, 10))
    for i in traces:
        for idx, model in enumerate(models):
            axs[i].bar(model, total_throughputs[i][idx], color=color[model])
        axs[i].set_title(f'Total Throughput in GPT-3 (trace: {traces[i]})')
        axs[i].set_ylabel('Throughput (samples/s)')