#!/usr/bin/env python3
# Copyright 2025 ETH Zurich and University of Bologna.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Lorenzo Leone <lleone@iis.ee.ethz.ch>

import argparse
import matplotlib.pyplot as plt
import numpy as np
from vc import experiments

HW_IMPLS = ['mp', 'pv', 'cb3', 'cb2']

LABELS = {
    'mp':  'Multiplane',
    'pv':  'Preemptive',
    'cb3': 'CreditBased - 3 input buffers',
    'cb2': 'CreditBased - 2 input buffers',
}

_cmap = plt.colormaps['plasma']
COLORS = {
    'baseline':     'black',
    'mp':           _cmap(0.10),
    'naive':        _cmap(0.70),
    'cb':           _cmap(0.40),
    'cb2':          _cmap(0.25),
    'cb3':          _cmap(0.40),
    'preemptvalid': _cmap(0.85),
    'pv':           _cmap(0.85),
}


def plot1(show=True):
    """Bar chart of total runtime in cycles per transfer size, grouped by HW implementation."""

    # Collect results for each HW implementation
    dfs = {}
    for hw_impl in HW_IMPLS:
        df = experiments.results(hw_impl=hw_impl)
        if 'total_cycles' not in df.columns:
            print(f'Warning: no perf results for {hw_impl}, skipping')
            continue
        dfs[hw_impl] = df.set_index('size')['total_cycles']

    if not dfs:
        print('No results available.')
        return

    sizes = sorted(next(iter(dfs.values())).index.tolist())
    n_impls = len(dfs)
    n_sizes = len(sizes)
    bar_width = 0.8 / n_impls
    x = np.arange(n_sizes)

    _, ax = plt.subplots()
    for i, hw_impl in enumerate([impl for impl in HW_IMPLS if impl in dfs]):
        offsets = x + (i - n_impls / 2 + 0.5) * bar_width
        values = [dfs[hw_impl].get(s, float('nan')) for s in sizes]
        ax.bar(offsets, values, width=bar_width, label=LABELS.get(hw_impl, hw_impl),
               color=COLORS.get(hw_impl))

    # Annotate cb2 overhead over cb3 for the three largest transfer sizes
    if 'cb2' in dfs and 'cb3' in dfs:
        impls_ordered = [impl for impl in HW_IMPLS if impl in dfs]
        cb2_i = impls_ordered.index('cb2')
        text_y_offset = {8192: 150, 16384: 150, 32768: 0}  #tune to move the slowdown text up/down
        arr_y_offset = {8192: 30, 16384: 100, 32768: 100}  #tune to move the slowdown text up/down
        for anno_size in [8192, 16384, 32768]:
            if anno_size not in sizes:
                continue
            anno_idx = sizes.index(anno_size)
            cb2_x  = anno_idx + (cb2_i - n_impls / 2 + 0.5) * bar_width
            cb2_y  = dfs['cb2'][anno_size]
            cb3_y  = dfs['cb3'][anno_size]
            arrow_x  = cb2_x - bar_width / 2 - 0.1
            slowdown = cb2_y / cb3_y
            ax.annotate(
                '', xy=(arrow_x, cb2_y + 0), xytext=(arrow_x, cb3_y + arr_y_offset[anno_size]),
                arrowprops=dict(arrowstyle='-|>', color='red', lw=0.7,
                                connectionstyle='arc3,rad=0',
                                shrinkA=0, shrinkB=0)
            )
            ax.text(arrow_x - 0.1, (cb3_y + cb2_y) / 2 + text_y_offset[anno_size], f'{slowdown:.2f}x',
                    color='red', ha='right', va='center', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([str(s) for s in sizes])
    ax.set_xlabel('Transfer size [B]')
    ax.set_ylabel('Runtime [cycles]')
    ax.set_axisbelow(True)
    ax.grid(True, axis='y', linestyle='-', color='gainsboro')
    ax.legend(labelspacing=0.4, handlelength=0.8, handleheight=0.8, handletextpad=0.5)

    plt.tight_layout()
    if show:
        plt.show()


# Kiviat data: one entry per implementation in order [naive, mp, pv, cb]
KIVIAT_IMPLS = ['naive', 'mp', 'pv', 'cb']

KIVIAT_LABELS = {
    'naive': 'Naive',
    'mp':    LABELS['mp'],
    'pv':    LABELS['pv'],
    'cb':    'CreditBased',
}

# Raw metric values in order [naive, mp, pv, cb]
# For lower-is-better metrics (area, routing, performance) the normalization
# uses min/v so that all axes mean "higher = better" and the best value = 1.
KIVIAT_DATA = {
    'Frequency\n[GHz]':          [1.43, 1.7,  1.7,  1.5 ],
    'Area\nefficiency':          [275,  270,   270,  350 ],
    'Routing\nefficiency':       [1600, 2800,  1600, 1606 ],
    'Performance':               [2800, 2800,  2800, 2800 ],
}

# True = higher raw value is better
KIVIAT_HIGHER_IS_BETTER = {
    'Frequency\n[GHz]':    True,
    'Area\nefficiency':    False,   # normalized as min/v
    'Routing\nefficiency': False,   # normalized as min/v
    'Performance':         False,   # normalized as min/v
}


def plot2(show=True):
    """Kiviat (radar) diagram comparing HW implementations across key metrics."""

    metrics = list(KIVIAT_DATA.keys())
    n_metrics = len(metrics)

    # Normalize to (0, 1] where 1.0 = best:
    #   higher-is-better → v / max(v)
    #   lower-is-better  → min(v) / v   (area/routing/perf efficiency)
    normalized = {}
    for metric, values in KIVIAT_DATA.items():
        mn, mx = min(values), max(values)
        if mn == mx:
            normalized[metric] = [1.0] * len(values)
        elif KIVIAT_HIGHER_IS_BETTER[metric]:
            normalized[metric] = [v / mx for v in values]
        else:
            normalized[metric] = [mn / v for v in values]

    angles = np.linspace(0, 2 * np.pi, n_metrics, endpoint=False).tolist()
    angles += angles[:1]

    _, ax = plt.subplots(subplot_kw=dict(polar=True))

    for i, impl in enumerate(KIVIAT_IMPLS):
        values = [normalized[m][i] for m in metrics] + [normalized[metrics[0]][i]]
        ax.plot(angles, values, label=KIVIAT_LABELS[impl], color=COLORS.get(impl))

    ax.set_thetagrids(np.degrees(angles[:-1]), metrics)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([])
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.15))

    plt.tight_layout()
    if show:
        plt.show()


def main():
    functions = [plot1, plot2]
    parser = argparse.ArgumentParser(description='Plot VC experiment results.')
    parser.add_argument(
        'plots',
        nargs='*',
        default='all',
        choices=[f.__name__ for f in functions] + ['all'],
        help='Plots to generate.'
    )
    args = parser.parse_args()

    def requested(plot):
        return plot in args.plots or 'all' in args.plots

    if requested('plot1'):
        plot1()
    if requested('plot2'):
        plot2()


if __name__ == '__main__':
    main()
