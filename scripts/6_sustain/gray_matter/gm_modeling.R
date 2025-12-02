
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
path.rois <- file.path(ROOT.OUTPUT, 'muse', 'amyloid_rois.csv')
path.muse.info <- file.path(ROOT.OUTPUT, 'muse', 'muse_dict.csv')

path.script <- normalizePath(file.path(this.dir(), '..', '..', 'rsource', 'longitudinal_change.R'))

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'atrophy', 'tmaps')
dir.create(odir, showWarnings = F, recursive = T)

# === Load data ======

# master
master <- read.csv(path.master)
master$Subtype <- ifelse(master$ControlForStaging == "True", 'Control', master$TrainingMLSubtype)

# merge in MUSE
muse <- read.csv(path.rois)
info <- read.csv(path.muse.info)
gm.cols <- info %>%
  filter(
    TissueType == 'GM',
    IsBrain == 'True',
    IsCerebellum == 'False',
    ! str_detect(Name, 'cerebral_exterior')
  ) %>%
  pull(Name) %>%
  str_c('_VOLUME')
merger <- muse[, c('Subject', 'Session', gm.cols)]
master <- left_join(master, merger, by = c('Subject', 'Session'))

# ICV normalization
master <- master %>%
  mutate(
    across(all_of(gm.cols), function(x) (x / ICV) * 1e6)
  )

# separate groups
training <- master %>%
  filter(
    Split == 'TrainingBaseline',
    (ControlForStaging == "True") | (TrainingMLStage != 0 &  TrainingSubtypeValid ==1 )
  )

# === Longitudinal change =======

source(path.script)

for (i in 1:length(gm.cols)) {
  print(sprintf('[%s/%s]', i, length(gm.cols)))
  training <- calc.longitudinal.change(
    training,
    master,
    gm.cols[i],
    date.column = 'TauAmyloidMeanDate',
    id.column = 'Subject',
    plot = F)
}

lm.cols <- str_c('Delta', gm.cols)

diff.to.t1 <- abs(difftime(
  ymd_hms(training$TauAmyloidMeanDate),
  ymd(training$ScanDateT1),
  units = 'days'
  )) / 365.25
omit <- diff.to.t1 >= 366
training[omit, lm.cols] <- NA

# === Model ======

subtypes <- c('S1', 'S2', 'S3')

has.longitudinal <- ! is.na(training[[lm.cols[1]]])

for (subtype in subtypes) {
  df <- training %>%
    filter(Subtype == subtype | Subtype == 'Control', has.longitudinal)
  print(sprintf('N observations: %s', nrow(df)))
  
  data <- vector(mode = 'list', length = length(gm.cols))
  
  for (i in 1:length(lm.cols)) {
    col <- lm.cols[i]
    fml <- as.formula(sprintf("%s ~ Subtype", col))
    
    m <- lm(fml, data = df)
    m.sum <- summary(m)
    m.table <- m.sum$coefficients
    result <- list(region = col, coefficient = m.table[2, 1], t = m.table[2, 3], p = m.table[2, 4])
    
    data[[i]] <- result
  }
  
  lm.table <- bind_rows(data)
  lm.table <- lm.table %>%
    mutate(
      p_adj = p.adjust(p, method = 'fdr'),
      t = ifelse(p_adj < 0.05, t, 0)
    )
  
  merger <- lm.table %>%
    mutate(
      Name = str_replace(region, '_VOLUME', ''),
      Name = str_replace(Name, 'Delta', ''),
      TVal = t
    ) %>%
    select(Name, TVal)
  
  to.image <- info %>%
    select(ROI, Name) %>%
    left_join(merger, by = 'Name')
  
  opath <- file.path(odir, sprintf('tmap_%s.csv', subtype))
  write.csv(to.image, opath, row.names = F)
}


