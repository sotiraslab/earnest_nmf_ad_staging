# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 14:24:36 2024

@author: earne
"""

from execute import execute

ANTS_PATH = '/export/ants/ants-2.4.0/bin'

def run_N4_bias_correction(inpath, outpath):
    
    call = [
        f'{ANTS_PATH}/N4BiasFieldCorrection',
        '-d', '3',
        '-i', inpath,
        '-o', outpath,
        '-v'
        ]
    
    execute(call)
    