library(car)
library(dplyr)
library(lubridate)
library(multcomp)
library(stringr)
library(this.path)
library(tidyr)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'
PATH.STATSFUNCS <- normalizePath(file.path(this.dir(), '..', '..', 'rsource', 'statsfuncs.R'))
source(PATH.STATSFUNCS)

# functions
residualize.loadings <- function(data) {
  cols <- colnames(data)
  pacs <- cols[str_detect(cols, 'PAC.*WScore')]
  ptcs <- cols[str_detect(cols, 'PTC.*WScore')]
  
  for (pac in pacs) {
    dest <- sprintf('%sResidualized', pac)
    fml <- as.formula(sprintf('%s ~ SummarySUVRAmyloid', pac))
    m <- lm(fml, data = data)
    data[[dest]] <- m$residuals
  }
  
  for (ptc in ptcs) {
    dest <- sprintf('%sResidualized', ptc)
    fml <- as.formula(sprintf('%s ~ SummarySUVRTau', ptc))
    m <- lm(fml, data = data)
    data[[dest]] <- m$residuals
  }
  
  return (data)
}

pipeline <- function(data) {
    dependents <- c(
      'Age', 'SexMale', 'Education', 'BMI', "HasE4", 'MMSETotal', 'CDRSumBoxes',
      colnames(data)[str_detect(colnames(data), 'Residualized')]
    )
    binary.dependents <- c('SexMale', 'HasE4')
    
    result.rows <- vector(mode = 'list', length = length(dependents))
    
    for (i in 1:length(dependents)) {
      dependent <- dependents[i]
      
      if (dependent %in% binary.dependents) {
        result.rows[[i]] <- run.chisq.binary.dependent(
          dependent = dependent,
          independent = 'StageType',
          data = data
        )
      } else {
        result.rows[[i]] <- run.ancova(
          dependent = dependent,
          independent = 'StageType',
          covariates = c('Age', 'SexMale'),
          data = data
          )
      }
    }
    
    result <- bind_rows(result.rows)
    pairwise.column <- str_detect(colnames(result), ' vs. ') # this could be improved but so be it
    missing.atypical <- ! str_detect(colnames(result), 'Atypical')
    result <- result[, ! (pairwise.column & missing.atypical)]
    
    # include multiple comparisons adjustment
    pair.cols <- colnames(result)[str_detect(colnames(result), ' vs. ')]
    id.cols <- colnames(result)[! colnames(result) %in% pair.cols]
    result.star <- result %>%
      mutate(across(all_of(pair.cols), function (x) ifelse(p < 0.05, x, NA))) %>%
      pivot_longer(all_of(pair.cols), names_to = 'Comparison', values_to = 'comp_p') %>%
      mutate(comp_p_adj = p.adjust(comp_p, method = 'fdr'),
             annot = as.character(cut(comp_p_adj,
                                      breaks = c(0, 0.001, 0.01, 0.05, Inf),
                                      labels = c('***', "**", "*", ""),
                                      include.lowest = T)),
             annot = ifelse(is.na(annot), '', annot),
             p = round(p, 3)
      ) %>%
      pivot_wider(id_cols = all_of(id.cols), names_from = Comparison, values_from = annot)
    
    return (result.star)
}

# RUN

# Load main data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_covariates.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA) %>%
  filter(Stage != 'A0T0') %>%
  mutate(StageType = ifelse(Stage == 'Atypical', 'Atypical', 'Typical'),
         StageType = ifelse(StageType == 'Typical' & Stage %in% c('A1T0', 'A2T0'), 'A1T0-A2T0', StageType),
         StageType = ifelse(StageType == 'Typical' & Stage %in% c('A2T1', 'A2T2', 'A2T3', 'A2T4'), 'A2T1-A2T4', StageType),
         StageType = factor(StageType, levels=c('Atypical', 'A1T0-A2T0', 'A2T1-A2T4'))
  )
training <- master %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False')
validation <- master %>%
  filter(Split == 'ValidationBaseline', ControlForStaging == 'False')

training <- residualize.loadings(training)
validation <- residualize.loadings(validation)
train.result <- pipeline(training)
validaiton.result <- pipeline(validation)

# Save
odir <- file.path(ROOT.OUTPUT, 'tables')
dir.create(odir, showWarnings = F)
write.csv(train.result, file.path(odir, 'training_atypical_modeling.csv'), row.names = F)
write.csv(validaiton.result, file.path(odir, 'validation_atypical_modeling.csv'), row.names = F)
