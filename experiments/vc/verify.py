#!/usr/bin/env python3
# Copyright 2025 ETH Zurich and University of Bologna.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0
#
# Lorenzo Leone <lleone@iis.ee.ethz.ch>
#
# Verification script for `multicast_benchmark.c` (vc experiment)

import sys
import snitch.util.sim.verif_utils as vu


class Verifier(vu.Verifier):

    OUTPUT_UIDS = ['output']

    def __init__(self):
        super().__init__()

    def get_actual_results(self):
        return self.get_output_from_symbol(self.OUTPUT_UIDS[0], 'uint32_t')

    def get_expected_results(self):
        length = int(self.get_input_from_symbol('length', 'uint32_t')[0])
        n_clusters = int(self.get_input_from_symbol('n_clusters', 'uint32_t')[0])
        return n_clusters * [i + 1 for i in range(length // n_clusters)]

    def check_results(self, *args):
        return super().check_results(*args, atol=0)


if __name__ == "__main__":
    sys.exit(Verifier().main())
