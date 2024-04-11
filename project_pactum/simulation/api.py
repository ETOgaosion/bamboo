import argparse
import collections
import json
import logging
import multiprocessing
import random
import statistics

from project_pactum.simulation.mysimulator import MySimulator

logger = logging.getLogger('project_pactum.simulation')

def parse(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int)
    parser.add_argument('--start-hour', type=int, choices=range(24))
    parser.add_argument('--generate-addition-probabilities', action='store_true')
    parser.add_argument('--removal-probability', type=float, default=None)
    parser.add_argument('--generate-graphs', action='store_true')
    parser.add_argument('--generate-table', action='store_true')
    parser.add_argument('--spot-instance-trace', type=str, default='traces/p3-trace.csv')
    parser.add_argument('--model', type=str, default='GPT-2')
    return parser.parse_args(args)

def graph(xlabel, xs, xmax, ylabel, ys, ymax, average,
          on_demand=None, out=None, show=False):
        import matplotlib.pyplot as plt

        # sizes: xx-small, x-small, small, medium, large, x-large, xx-large
        params = {
            'legend.fontsize': 'x-small',
            'axes.labelsize': 'x-small',
            'axes.titlesize': 'x-small',
            'xtick.labelsize': 'x-small',
            'ytick.labelsize': 'x-small',
            'figure.figsize': (3.0, 1.7),
        }
        plt.rcParams.update(params)

        plt.clf()

        plt.plot(xs, ys, linewidth=0.5)

        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        for scale in [1, 2, 6, 12, 24, 48, 72]:
            xticks = list(range(0, xmax + 1, scale))
            if len(xticks) < 7:
                break
        if xmax not in xticks:
            xticks.append(xmax)
        plt.xticks(xticks)

        plt.xlim(0, xmax)
        plt.ylim(0, ymax)

        plt.hlines(average, 0, xmax, color='tab:blue', linestyles='dotted')
        if on_demand is not None:
            plt.hlines(on_demand, 0, xmax, color='tab:red', linestyles='dashed')

        ax = plt.gca()
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)

        if out is not None:
           plt.savefig(
               out,
               bbox_inches='tight',
               pad_inches=0
           )

        if show:
            plt.show()

def simulate(args):
    model, duration, spot_instance_trace = args
    print(args)
    simulator = MySimulator(
        seed=0,
        start_hour=0,
        generate_addition_probabilities=True,
        removal_probability=0,
        spot_instance_trace=spot_instance_trace,
        model=model
    )
    result = simulator.simulate(duration=duration)
    return result

def generate_table(model='GPT-2', spot_instance_trace='trace/p3-trace.csv', duration=4_320_000):
    logging.getLogger('project_pactum.simulation.simulator').setLevel(logging.INFO)


    result = simulate([model, duration, spot_instance_trace])

    print('Probability', 'Preemptions', 'Interruptions', 'Lifetimes', 'Fatal Failures', 'Instances', 'Performance', '     Cost', '    Value',
          sep=' & ', end=' \\\\\n')
    print(f'{result.removal_probability:11.2f}',
        '{:11.2f}'.format(result.preemption_mean),
        '{:13.2f}'.format(result.num_preemptions),
        '{:9.2f}'.format(result.lifetime_mean),
        '{:14.2f}'.format(result.num_fatal_failures),
        '{:9.2f}'.format(result.average_instances),
        '{:11.2f}'.format(result.average_performance),
        '{:9.2f}'.format(result.average_cost),
        '{:9.2f}'.format(result.average_value),
        sep=' & ', end=' \\\\\n'
        )

def main(args):
    from project_pactum.core.base import setup_logging
    setup_logging()

    options = parse(args)
    print(options)

    assert not (options.generate_graphs and options.generate_table)

    if not options.generate_table:
        simulator = MySimulator(
            seed=options.seed,
            start_hour=options.start_hour,
            generate_addition_probabilities=options.generate_addition_probabilities,
            removal_probability=options.removal_probability,
            generate_graphs=options.generate_graphs,
            spot_instance_trace=options.spot_instance_trace,
            model=options.model
        )
        # simulator.simulate()
        simulator.simulate(duration=4_320_0000)
        # simulator.simulate(duration=1_200_000)
    else:
        generate_table(options.model, spot_instance_trace=options.spot_instance_trace, duration=4_320_0000)
