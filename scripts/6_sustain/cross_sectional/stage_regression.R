library(dplyr)
library(ggalluvial)
library(ggplot2)
library(lubridate)
library(stringr)
library(this.path)
library(tidyr)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'stage_regression')
dir.create(odir, showWarnings = F)


# Load data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA)
master$Subtype <- factor(master$TrainingMLSubtype, levels = c('S1', 'S2', 'S3'))
master$Stage <- master$TrainingMLStage

# data selection
training <- master %>%
  filter(
    Split == 'TrainingBaseline',
    ControlForStaging == "False",
    TrainingMLStage != 0,
    TrainingSubtypeValid ==1
  )

data <- training
y <- 'SummarySUVRTau'

# model
fml <- as.formula(sprintf('%s ~ Stage * Subtype', y))
m <- lm(fml, data=data)
em <- emmeans(m, 'Subtype')
em.pairs <- summary(pairs(em, adjust='fdr'))

# plot
colors <- c(
  'Control' = 'gray',
  'S1' = '#db2b39',
  'S2' = '#053c5e',
  'S3' = '#f3a712' 
)

ggplot(data = training, aes(x = Stage, y = !!sym(y), fill = Subtype, color=Subtype)) +
  geom_point(position = position_jitter(), alpha = 0.3, shape=19) +
  geom_smooth(method = 'lm') + 
  scale_fill_manual(values = colors) +
  scale_color_manual(values = colors) +
  theme(text = element_text(size = 14)) +
  theme_light() +
  scale_x_continuous(breaks = 1:11)
