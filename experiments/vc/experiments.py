#!/usr/bin/env python3
# Copyright 2025 ETH Zurich and University of Bologna.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Lorenzo Leone <lleone@iis.ee.ethz.ch>
#
# Experiment sweep for evaluating the impact of virtual channels on
# data transers``. Always uses IMPL=TREE and N_ROWS=4; only SIZE
# is swept.

import math
from pathlib import Path
import gwaihir as pb
import snitch.util.experiments.experiment_utils as eu
from snitch.util.experiments.SimResults import SimRegion

N_ROWS = 4
LOG2_N_ROWS = 2
N_CLUSTERS_PER_ROW = 4
TCK = 5
IMPL = "TREE"
DIR = Path(__file__).parent

TREE_ROI = DIR / 'roi/tree.json'


###############
# Experiments #
###############

class ExperimentManager(pb.ExperimentManager):

    def __init__(self, *args, hw_impl='default', **kwargs):
        self.hw_impl = hw_impl
        super().__init__(*args, **kwargs)

    def derive_name(self, experiment):
        return f'{self.hw_impl}/{experiment["size"]}'

    def derive_axes(self, experiment):
        return eu.derive_axes_from_keys(experiment, ['size'])

    def derive_cdefines(self, experiment):
        return {
            'IMPL':        IMPL,
            'LOG2_N_ROWS': LOG2_N_ROWS,
            'SIZE':        experiment['size'],
        }

    def derive_hw_cfg(self, experiment):
        return pb.hw_cfg


def gen_experiments(ci=False):
    sizes = [1024, 2048, 4096, 8192, 16384, 32768]
    if ci:
        sizes = [32768]

    experiments = []
    for size in sizes:
        experiments.append({
            'impl':   'tree',
            'n_rows': N_ROWS,
            'size':   size,
            'app':    'multicast_benchmark',
            'cmd':    pb.sim_and_verify_cmd(Path.cwd() / 'verify.py'),
            'roi':    TREE_ROI,
        })
    return experiments


###########
# Results #
###########

def dma_core(cluster_idx):
    return f'hart_{1 + cluster_idx * 9 + 8}'


def total_cycles(sim_results):
    """End-to-end latency: from L3 fetch on cluster 0 to last col-tree send."""
    n_levels = int(math.log2(N_CLUSTERS_PER_ROW * N_ROWS) + 1)
    start = SimRegion(dma_core(0), 'level 0', 0)
    end = SimRegion(dma_core(2 * N_CLUSTERS_PER_ROW), f'level {n_levels - 1}', 0)
    return sim_results.get_timespan(start, end) // TCK


def m2c_cycles(sim_results):
    """Memory-to-cluster latency: L3 -> cluster 0."""
    return sim_results.get_timespan(SimRegion(dma_core(0), 'level 0', 0)) // TCK


def c2c_cycles(sim_results):
    """Cluster-to-cluster latency: cluster 0 -> cluster 8 (first hop)."""
    return sim_results.get_timespan(SimRegion(dma_core(0), 'level 1', 0)) // TCK


def results(manager=None, hw_impl='default'):
    if manager is None:
        manager = ExperimentManager(gen_experiments(), dir=DIR, parse_args=False,
                                    hw_impl=hw_impl)
    df = manager.get_results()
    if manager.perf_results_available:
        df['total_cycles'] = df['results'].apply(total_cycles)
        df['m2c_cycles'] = df['results'].apply(m2c_cycles)
        df['c2c_cycles'] = df['results'].apply(c2c_cycles)
    return df


########
# Main #
########

def main():
    parser = ExperimentManager.parser()
    parser.add_argument('--ci', action='store_true',
                        help='Reduce experiment space for CI runs')
    parser.add_argument('--hw-impl', default='default',
                        help='HW implementation tag used to namespace run/build directories')
    args = parser.parse_args()
    manager = ExperimentManager(gen_experiments(ci=args.ci), dir=DIR, args=args,
                                parse_args=False, hw_impl=args.hw_impl)
    manager.run()
    df = results(manager, hw_impl=args.hw_impl)
    print(df)


if __name__ == '__main__':
    main()
