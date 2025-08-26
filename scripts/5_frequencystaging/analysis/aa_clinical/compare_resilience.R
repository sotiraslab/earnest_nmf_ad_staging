library(dplyr)
library(gt)
library(gtsummary)
library(stringr)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'
MUSE.VALUES <- '/Users/earnestt1234/Desktop/_muse_tau.csv'
MUSE.ROIS <- '/Users/earnestt1234/Desktop/muse_rois_clean.csv'

# Load main data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_clinical_stages.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA) %>%
  filter(AA2024Clinical != '',
         ResilientVulnerable %in% c('Expected', 'Vulnerable', 'Resilient')) %>%
  mutate(ResilientVulnerable = factor(ResilientVulnerable))

# Load muse
muse.rois <- read.csv(MUSE.ROIS)
muse.values <- read.csv(MUSE.VALUES)

volume.regions <- muse.rois[muse.rois$TissueType == 'GM' & muse.rois$IsCerebellum == 'False', 'Name']
volume.region.cols <- str_c(volume.regions, '_VOLUME')
vols <- muse.values[, volume.region.cols] %>%
  select(-contains('cerebral_exterior'))

# training <- master %>%
#   filter(Split == 'TrainingBaseline', ControlForStaging == 'False')
# validation <- master %>%
#   filter(Split == 'ValidationBaseline', ControlForStaging == 'False')
# 
# my.table <- training %>%
#   dplyr::select(
#     ResilientVulnerable,
#     Age,
#     SexMale,
#     Education,
#     BMI,
#     HasE4) %>%
#   tbl_summary(
#     by = ResilientVulnerable,
#     digits = all_continuous() ~ 2,
#     missing = 'no',
#     statistic = list(
#       all_continuous() ~ "{mean} ({sd})",
#       all_categorical() ~ "{n} ({p}%)"
#     )
#   ) %>%
#   add_p(test = list(all_continuous() ~ 'oneway.test'),
#         test.args=all_tests("fisher.test")~list(simulate.p.value=TRUE)
#         ) %>%
#   add_q(method='fdr')
# 
# print(my.table)