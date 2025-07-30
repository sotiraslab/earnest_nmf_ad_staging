import numpy as np
import pandas as pd

def assign_frequency_stage(data, groupings=None, p='any', atypical='NS'):

    if groupings is None:
        groupings = list(range(data.shape[1]))

    unique_stages = sorted(list(set(groupings)))
    n = len(unique_stages)
    stage_mat = np.zeros((len(data), n))

    for i in unique_stages:
        regions_in_stage = (np.array(groupings) == i)
        n_regions_in_stage = regions_in_stage.sum()
        sub = data[:, regions_in_stage]
        freqs = sub.sum(axis=1) / n_regions_in_stage

        if p == 'any':
            positive = freqs > 0
        elif p == 'all':
            positive = freqs == 1
        else:
            positive = freqs >= p

        stage_mat[:, i] = positive

    diffs = np.diff(stage_mat, axis=1)
    if n == 2:
        increasing = diffs <= 0
    else:
        increasing = np.all(diffs <= 0, axis=1)
    stage = np.where(increasing, stage_mat.sum(axis=1).astype(int), atypical)

    cats = [str(i) for i in range(0, len(unique_stages) + 1)] + [str(atypical)]
    return pd.Categorical(stage, categories=cats)