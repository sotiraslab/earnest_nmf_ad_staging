import json
import os

from atstaging.config import get, set_config
from atstaging.outputs import load_subtyped_data

set_config('main')
root_output = get('output_directory')

odir = os.path.join(root_output, 'wta_json', 'wscore_averages')
os.makedirs(odir, exist_ok=True)

def pipeline(split):

    df = load_subtyped_data(split)
    subtype_col = f'{split.capitalize()}MLSubtype'
    stage_col = f'{split.capitalize()}MLStageBinned'

    cols = df.columns[df.columns.str.contains('WScore')]
    df = df[[subtype_col, stage_col] + list(cols)].copy()

    wmean = df.groupby([subtype_col, stage_col]).mean().reset_index()

    for index in wmean.index:
        subtype = wmean.loc[index, subtype_col]
        stage = wmean.loc[index, stage_col]
        stage = stage.replace('+', 'plus')
        data = wmean.loc[index, cols].to_dict()
        data = {k.replace('WScore', ''):v for k, v in data.items()}

        opath = os.path.join(odir, f'wscores_{split}_{subtype}_{stage}.json')
        with open(opath, 'w') as f:
            json.dump(data, f, indent=4)

    return wmean

train = pipeline('training')
val = pipeline('validation')
