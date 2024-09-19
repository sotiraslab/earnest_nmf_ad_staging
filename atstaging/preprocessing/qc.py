#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 10:48:35 2024

@author: earnestt1234
"""

from nifti_overlay import NiftiOverlay

def skullstripping_qc_image(t1, brainmask, output):
    overlay = NiftiOverlay(verbose=True, dpi=300)
    overlay.add_anat(t1)
    overlay.add_mask(brainmask, color='red', alpha=0.5)
    overlay.generate(output)

def registration_checkerboard_qc_image(registered, template, output):
    overlay = NiftiOverlay(verbose=True, dpi=300)
    overlay.add_checkerboard([registered, template])
    overlay.generate(output)
