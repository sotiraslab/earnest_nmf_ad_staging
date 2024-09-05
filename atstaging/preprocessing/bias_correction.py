# -*- coding: utf-8 -*-
"""
Created on Wed Sep  4 14:24:36 2024

@author: earne
"""

import subprocess
ANTS_PATH = '/Users/earne/MyTools/ants-2.5.3/bin'

def execute(cmd):
    popen = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True)
    for line in popen.stdout:
        print(line, end='')
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def run_N4_bias_correction(inpath, outpath):
    
    call = [
        f'{ANTS_PATH}/N4BiasFieldCorrection',
        '-d', '3',
        '-i', inpath,
        '-o', outpath,
        '-v'
        ]
    
    execute(call)
    