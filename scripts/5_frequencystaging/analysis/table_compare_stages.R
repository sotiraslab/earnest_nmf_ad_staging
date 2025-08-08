library(dplyr)
library(gt)
library(gtsummary)
library(lubridate)
library(stringr)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

# Load main data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_covariates.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA)
training <- master %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False')
validation <- master %>%
  filter(Split == 'ValidationBaseline', ControlForStaging == 'False')

# function for making table

staging.table <- function(df, savepath=NULL) {
  my.table <- df %>%
    select(
      Stage,
      Age,
      SexMale,
      Education,
      BMI,
      CDRBinned,
      CDRSumBoxes,
      MMSETotal,
      SummarySUVRAmyloid,
      SummarySUVRTau) %>%
    rename(
      Male=SexMale,
      MMSE=MMSETotal,
      "CDR (Sum of boxes)"=CDRSumBoxes,
      "Amyloid SUVR"=SummarySUVRAmyloid,
      "Tau SUVR"=SummarySUVRTau
    ) %>%
    mutate(
      "CDR=0.0" = CDRBinned == '0.0',
      "CDR=0.5" = CDRBinned == '0.5',
      "CDR>=1.0" = CDRBinned == '1.0+',
      .after = BMI
    ) %>%
    select(
      -CDRBinned
    ) %>%
    tbl_summary(
      by = Stage,
      digits = all_continuous() ~ 2,
      missing = 'no',
      statistic = list(
        all_continuous() ~ "{mean} ({sd})",
        all_categorical() ~ "{n} ({p}%)"
      )
    ) %>%
    add_p(test = list(all_continuous() ~ 'oneway.test'),
          test.args=all_tests("fisher.test")~list(simulate.p.value=TRUE))
  
  print(my.table)
  
  if (! is.null(savepath)) {
    gtsave(as_gt(my.table), savepath)
  }
}

# Run
staging.table(training, savepath = file.path(PATH.OUTPUT, 'training_stages.docx'))
staging.table(validation, savepath = file.path(PATH.OUTPUT, 'validation_stages.docx'))

