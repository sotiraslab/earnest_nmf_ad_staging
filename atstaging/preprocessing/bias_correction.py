# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 14:24:36 2024

@author: earne
"""

from execute import execute

from atstaging.config import get

def run_N4_bias_correction(inpath, outpath):
    
    ants = get('ants')
    
    call = [
        f'{ants}/N4BiasFieldCorrection',
        '-d', '3',
        '-i', inpath,
        '-o', outpath,
        '-v'
        ]
    
    execute(call)
    