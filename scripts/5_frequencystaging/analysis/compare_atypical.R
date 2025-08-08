library(dplyr)
library(lubridate)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

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

m <- lm(PACParietalSUVR ~ StageType + SummarySUVRTau + SummarySUVRAmyloid, data = training)
summary(m)
# TukeyHSD(m)

emmeans_test(data = training, formula = PACFrontalSUVR ~ StageType, covariate = SexMale, p.adjust.method = "fdr")