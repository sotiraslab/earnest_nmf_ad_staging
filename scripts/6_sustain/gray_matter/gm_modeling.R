
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
    across(all_of(gm.cols), function(x) x / ICV)
  )

# separate groups
training <- master %>%
  filter(
    Split == 'TrainingBaseline',
    (ControlForStaging == "True") | (TrainingMLStage != 0 &  TrainingSubtypeValid ==1 )
  )

# === Model ======

subtype <- 'S2'

df <- training %>%
  filter(Subtype == subtype | Subtype == 'Control')

data <- vector(mode = 'list', length = length(gm.cols))

for (i in 1:length(gm.cols)) {
  col <- gm.cols[i]
  fml <- as.formula(sprintf("%s ~ Subtype", col))
  
  # control.mask <- df$Subtype == 'Control'
  # control.data <- df[control.mask, col]
  # df[[col]] <- (df[[col]] - mean(control.data)) / (sd(control.data))
  # 
  m <- lm(fml, data = df)
  m.sum <- summary(m)
  m.table <- m.sum$coefficients
  result <- list(region = col, coefficient = m.table[2, 1], t = m.table[2, 3], p = m.table[2, 4])
  
  data[[i]] <- result
}

lm.table <- bind_rows(data)
lm.table <- lm.table %>%
  mutate(
    t = ifelse(p < 0.05, t, 0)
  )

# =======

merger <- lm.table %>%
  mutate(
    Name = str_replace(region, '_VOLUME', ''),
    TVal = t
  ) %>%
  select(Name, TVal)

to.image <- info %>%
  select(ROI, Name) %>%
  left_join(merger, by = 'Name')

write.csv(to.image, '~/Desktop/muse_to_image.csv', row.names = F)