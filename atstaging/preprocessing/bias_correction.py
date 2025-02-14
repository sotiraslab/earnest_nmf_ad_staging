# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 14:24:36 2024

@author: earne
"""

from .execute import execute, get_cli_path

def run_N4_bias_correction(inpath, outpath):

    n4 = get_cli_path('N4BiasFieldCorrection')

    call = [
        n4,
        '-d', '3',
        '-i', inpath,
        '-o', outpath,
        '-v'
        ]

    execute(call)
