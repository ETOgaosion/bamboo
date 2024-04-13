import matplotlib.pyplot as plt

def graph_together(axis, xlabel, xs, xmax, ylabel, ys, ymax, average,
          on_demand=None):
    axis.plot(xs, ys, linewidth=0.5)

    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)

    for scale in [1, 2, 6, 12, 24, 48, 72]:
        xticks = list(range(0, xmax + 1, scale))
        if len(xticks) < 7:
            break
    if xmax not in xticks:
        xticks.append(xmax)
    axis.set_xticks(xticks)

    axis.set_xlim(0, xmax)
    axis.set_ylim(0, ymax)
    axis.spines['right'].set_visible(False)
    axis.spines['top'].set_visible(False)

    axis.hlines(average, 0, xmax, color='tab:blue', linestyles='dotted')
    if on_demand is not None:
        axis.hlines(on_demand, 0, xmax, color='tab:red', linestyles='dashed')

def graph(xlabel, xs, xmax, ylabel, ys, ymax, average,
          on_demand=None, out=None, show=False, clf=True):

    # sizes: xx-small, x-small, small, medium, large, x-large, xx-large
    params = {
        'legend.fontsize': 'x-small',
        'axes.labelsize': 'x-small',
        'axes.titlesize': 'x-small',
        'xtick.labelsize': 'x-small',
        'ytick.labelsize': 'x-small',
        'figure.figsize': (15.0, 5.0),
    }
    plt.rcParams.update(params)

    if clf:
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
            pad_inches=0.25
        )

    if show:
        plt.show()