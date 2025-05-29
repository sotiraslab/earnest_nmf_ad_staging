# imports
library(dplyr)
library(gtools)

# Set paths
PATH.MASTER <- '/scratch/tom.earnest/atstaging/masterTables/_hardsave.csv' # see hardsave_master.py
PATH.WSCORE.SCRIPT <- '/home/tom.earnest/code/at_nmf_sustain/scripts/rsource/wscore.R'
PATH.OUTPUT <- '/scratch/tom.earnest/atstaging/masterTables/FEATURE_WSCORES.csv'

# parameters
covariates <- c('Age', 'SexMale')
match.continuous <- c('Age', 'SummarySUVRAmyloid', 'SummarySUVRTau')
match.categorical <- c('SexMale')
portion.train <- 0.8
repeats <- 200
seed <- T

# load scripts
source(PATH.WSCORE.SCRIPT)

# load data
master <- read.csv(PATH.MASTER)

# subset data
train.all <- master[grepl('Training', master$Split), ]
train.bl <- master[master$Split == 'TrainingBaseline', ]
train.control <- train.bl[(!is.na(train.bl$CDRBinned)) & (train.bl$CDRBinned == '0.0') & (train.bl$FinalAmyloidStatus == 0) & (train.bl$GMMTauStatus == 0), ]

valA.all <- master[master$SameTracerValidationA == 'True', ]
valA.bl <- valA.all[grepl('Baseline', valA.all$Split), ]
valA.control <- valA.bl[(!is.na(valA.bl$CDRBinned)) & (valA.bl$CDRBinned == '0.0') & (valA.bl$FinalAmyloidStatus == 0) & (valA.bl$GMMTauStatus == 0), ]

valB.all <- master[master$SameTracerValidationB == 'True', ]
valB.bl <- valB.all[grepl('Baseline', valB.all$Split), ]
valB.control <- valB.bl[(!is.na(valB.bl$CDRBinned)) & (valB.bl$CDRBinned == '0.0') & (valB.bl$FinalAmyloidStatus == 0) & (valB.bl$GMMTauStatus == 0), ]

valC.all <- master[master$SameTracerValidationC == 'True', ]
valC.bl <- valC.all[grepl('Baseline', valC.all$Split), ]
valC.control <- valC.bl[(!is.na(valC.bl$CDRBinned)) & (valC.bl$CDRBinned == '0.0') & (valC.bl$FinalAmyloidStatus == 0) & (valC.bl$GMMTauStatus == 0), ]


# report sizes
report.sizes <- function(name, df.all, df.bl, df.control) {
    cat('\n')
    cat('\nSPLIT=', name)
    cat('\n  - BL + LONG: ', nrow(df.all))
    cat('\n  - BL : ', nrow(df.bl))
    cat('\n  - CONTROL : ', nrow(df.control))
    cat('\n')
}

report.sizes('Training set', train.all, train.bl, train.control)
report.sizes('Validation A', valA.all, valA.bl, valA.control)
report.sizes('Validation B', valB.all, valB.bl, valB.control)
report.sizes('Validation C', valC.all, valC.bl, valC.control)

# identify W-score columns
wscore.inputs <- colnames(master)[grepl('PAC.*|PTC.*', colnames(master), perl = T)]

# helper function for W-scoring
wscore.routine <- function(fulldata, control.subset) {
    wmodel <- repeated.wscore.train(
      control.data = control.subset,
      y = wscore.inputs,
      covariates = covariates,
      match.continuous = match.continuous,
      match.categorical = match.categorical,
      portion.train = portion.train,
      repeats = repeats,
      seed = seed
    )

    predicts <- repeated.wscore.predict(wmodel, fulldata)
    cat('\nSum of NAs for predictions:', sum(is.na(predicts)), '\n\n')
    wscore.outputs <- gsub('SUVR', 'WScore', colnames(predicts))
    colnames(predicts) <- wscore.outputs

    wdf <- cbind(fulldata[, c('Subject', 'Session')], predicts)
    return (wdf)
    
}

# W-Scoring
train.wdf <- wscore.routine(fulldata = train.all, control.subset = train.control)
valA.wdf <- wscore.routine(fulldata = valA.all, control.subset = valA.control)
valB.wdf <- wscore.routine(fulldata = valB.all, control.subset = valB.control)
valC.wdf <- wscore.routine(fulldata = valC.all, control.subset = valC.control)

# save output as features
wscores <- bind_rows(train.wdf, valA.wdf, valB.wdf, valC.wdf)
write.csv(wscores, PATH.OUTPUT, quote=F, na='', row.names=F)
