# imports
library(dplyr)
library(gtools)

# Set paths
PATH.MASTER <- '/scratch/tom.earnest/atstaging/masterTables/_hardsave.csv' # see hardsave_master.py
PATH.WSCORE.SCRIPT <- '/home/tom.earnest/code/at_nmf_sustain/scripts/rsource/wscore.R'
PATH.OUTPUT <- '/scratch/tom.earnest/atstaging/masterTables/FEATURE_TRAINING_WSCORES'

# load data
master <- read.csv(PATH.MASTER)

# load scripts
source(PATH.WSCORE.SCRIPT)

# W-scoring
train <- master[master$Split == 'TrainingBaseline', ]
control <- train[(!is.na(train$CDRBinned)) & (train$CDRBinned == '0.0') & (train$FinalAmyloidStatus == 0) & (train$GMMTauStatus == 0), ]
wscore.cols <- colnames(train)[grepl('PAC.*|PTC.*', colnames(train), perl = T)]

wmodel <- repeated.wscore.train(
  control.data = control,
  y = wscore.cols,
  covariates = c('Age', 'SexMale'),
  match.continuous = c('Age', 'SummarySUVRAmyloid', 'SummarySUVRTau'),
  match.categorical = c('SexMale'),
  portion.train = 0.8,
  repeats = 200,
  seed = T
)

# Save the W-scores
# only apply model to datasets with same tracer combo
applyto <- master[grepl('Training', master$Split), ]
predicts <- repeated.wscore.predict(wmodel, applyto)
wscore.columns.final <- gsub('SUVR', 'WScore', colnames(predicts))
colnames(predicts) <- wscore.columns.final 
wscores <- cbind(applyto[, c('Subject', 'Session')], predicts)

# Save