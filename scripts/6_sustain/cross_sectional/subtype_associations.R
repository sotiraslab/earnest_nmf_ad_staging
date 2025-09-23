
# === Imports ======

library(dplyr)
library(ggplot2)
library(stringr)
library(this.path)
library(tibble)
library(tidyr)

# === Setup ======
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging'
path.master <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')

colors <- c(
  'Control' = 'gray',
  'S1' = '#db2b39',
  'S2' = '#053c5e',
  'S3' = '#f3a712' 
)

control.name <- 'Control'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'cross_sectional_associations')
dir.create(odir, showWarnings = F)

# === Load ANOVA helper funcs ======

path.anova <- normalizePath(file.path(this.dir(), '..', '..', 'rsource', 'anova.R'))
source(path.anova)

# === Load data ======

master <- read.csv(path.master)
master$TauLaterality <- abs(master$PTCLeftParietalTemporalWScore - master$PTCRightParietalTemporalWScore)
master$Subtype <- ifelse(master$ControlForStaging == "True", control.name, master$TrainingMLSubtype)

training <- master %>%
  filter(
    Split == 'TrainingBaseline',
    ControlForStaging == "False",
    TrainingMLStage != 0,
    TrainingSubtypeValid ==1
  )

validation <- master %>%
  filter(
    Split == 'ValidationBaseline',
    ControlForStaging == "False",
    TrainingMLStage != 0,
    TrainingSubtypeValid ==1
  )

# === Helper functions ======

pipeline <- function(split, y, sig.y.start = 1, sig.y.gap = 1, y_lab=NULL) {
  
  data <- list('training' = training, 'validation' = validation)[[split]]
  
  result <- anova.plot(x = 'Subtype', y = y, data = data, colors = colors,
                       correction = 'fdr', sig.y.start = sig.y.start,
                       sig.y.gap = sig.y.gap, y_lab = y_lab)
  
  # save stuff
  stub <- sprintf('%s_%s', y, split)
  
  # save plot
  
  pname <- sprintf('%s_swarmplot.svg', stub)
  ggsave(file.path(odir, pname), height = 6, width = 4, units = 'in')
  
  # save anova
  aname <- sprintf('%s_anova.csv', stub)
  anova <- result$anova
  anova.table <- summary(anova)[[1]]
  write.csv(anova.table, file.path(odir, aname), row.names = F)
  
  # save posthoc 
  sname <- sprintf('%s_posthoc.csv', stub)
  posthoc <- result$posthoc
  write.csv(posthoc, file.path(odir, sname), row.names = F)
}

# === Run ======

# Training
result <- pipeline('training', 'Age', sig.y.start = 92, sig.y.gap = 2)
result <- pipeline('training', 'Education', sig.y.start = 25, sig.y.gap = 2)
result <- pipeline('training', 'SummarySUVRAmyloid', sig.y.start = 2.25, sig.y.gap = .1, y_lab = 'Amyloid (SUVR)')
result <- pipeline('training', 'SummarySUVRTau', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Tau (SUVR)')
result <- pipeline('training', 'TauLaterality', sig.y.start = 10, sig.y.gap = 1, y_lab = 'Tau Laterality')
result <- pipeline('training', 'CDRSumBoxes', sig.y.start = 8, sig.y.gap = 1, y_lab = 'CDR (sum of boxes)')
result <- pipeline('training', 'MMSETotal', sig.y.start = 31, sig.y.gap = 1.2, y_lab = 'MMSE')

# Validation
result <- pipeline('validation', 'Age', sig.y.start = 92, sig.y.gap = 2)
result <- pipeline('validation', 'Education', sig.y.start = 22, sig.y.gap = 2)
result <- pipeline('validation', 'SummarySUVRAmyloid', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Amyloid (SUVR)')
result <- pipeline('validation', 'SummarySUVRTau', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Tau (SUVR)')
result <- pipeline('validation', 'TauLaterality', sig.y.start = 10, sig.y.gap = 1, y_lab = 'Tau Laterality')
result <- pipeline('validation', 'CDRSumBoxes', sig.y.start = 8, sig.y.gap = 1, y_lab = 'CDR (sum of boxes)')
result <- pipeline('validation', 'MMSETotal', sig.y.start = 31, sig.y.gap = 1.2, y_lab = 'MMSE')
