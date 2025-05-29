"""The master table is usually loaded dynamically as a pandas dataframe
using Python routines. Rather than reimplementing that in R, this script
is used to make the table accessible to R prior to doing the staging functions
which are R-dependent."""

from atstaging.config import set_config
from atstaging.outputs import load_split

# where the table is saved
OUTPATH = '/scratch/tom.earnest/atstaging/masterTables/_hardsave.csv'

# main
set_config('main')
df = load_split(split=None, longitudinal=None)
df.to_csv(OUTPATH, index=False)



