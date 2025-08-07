library(dplyr)
library(gt)
library(gtsummary)
library(lubridate)
library(stringr)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

# Load data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_covariates.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT)

master <- read.csv(PATH.DATA)
master$TauAmyloidMeanDate <- as_datetime(ymd_hms(master$TauAmyloidMeanDate))

# Create (pretty) data for table
df <- master %>%
  group_by(Subject) %>%
  summarise(
    Group = first(Split),
    Control = first(ControlForStaging),
    Age = first(Age),
    Sex = first(SexMale),
    Race = first(Race),
    Hispanic = first(Hispanic),
    Education = first(Education),
    BMI = first(BMI),
    CDR = first(CDRBinned),
    APOEE4 = first(HasE4),
    "Amyloid-PET tracer" = first(TracerAmyloid),
    "Tau-PET tracer" = first(TracerTau),
    "Amyloid SUVR" = first(SummarySUVRAmyloid),
    "Tau SUVR" = first(SummarySUVRTau),
    Visits = as.numeric(n()),
    DateFirst = first(TauAmyloidMeanDate),
    DateLast = last(TauAmyloidMeanDate)
    ) %>%
  ungroup() %>%
  mutate(
    Sex = factor(ifelse(Sex == 1, 'M', 'F'), levels = c('M', 'F')),
    Disease = ifelse(Control == 'True', 'NC', 'ADS'),
    Split = str_extract(Group, '(Training|Validation)'),
    SplitDisease = str_c(Split, '-', Disease),
    CDR = ifelse(CDR == '', NA, CDR),
    CDR = factor(CDR, levels = c('0.0', '0.5', '1.0+')),
    Race = ifelse(Race == '', NA, Race),
    Race = factor(Race, levels = c('White', 'Black', "Asian", 'Other')),
    APOEE4 = ifelse(APOEE4 == 1, 'Positive', 'Negative'),
    Followup = as.numeric(difftime(DateLast, DateFirst, units = 'days') / 365.25),
    "Followup (y)" = ifelse(Followup == 0, NA, Followup)
    ) %>%
  select(-Disease, -Group, -Control, -DateFirst, -DateLast, -Followup)

# Table splitting training and validation
df %>%
  select(-Subject, -SplitDisease) %>%
  tbl_summary(
    by = Split,
    digits = all_continuous() ~ 2,
    missing = 'no',
    statistic = list(
      all_continuous() ~ "{mean} ({sd})",
      all_categorical() ~ "{n} ({p}%)"
    )
  ) %>%
  add_n() %>%
  add_p(test = list(all_continuous() ~ "t.test"), include = -Visits) %>%
  as_gt() %>%
  gtsave(file.path(PATH.OUTPUT, 'gtsummary_by_split.docx')) 

# Table splitting training and validation and disease status
df %>%
  select(-Subject, -Split) %>%
  tbl_summary(
    by = SplitDisease,
    digits = all_continuous() ~ 2,
    missing = 'no',
    statistic = list(
      all_continuous() ~ "{mean} ({sd})",
      all_categorical() ~ "{n} ({p}%)"
    )
  ) %>%
  add_n() %>%
  add_p(test = list(all_continuous() ~ 'oneway.test'), include = -Visits) %>%
  as_gt() %>%
  gtsave(file.path(PATH.OUTPUT, 'gtsummary_by_split_disease.docx')) 