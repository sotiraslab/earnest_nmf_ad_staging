
library(dplyr)
library(ggplot2)
library(tidyr)

ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

master.path <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
master <- read.csv(master.path)

df <- master %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False', TrainingMLStage != 0)

df$Indicator <- df$TrainingMLSubtype == 'S1'
m <- lm(PTCLeftParietalTemporalWScore ~ Indicator, data = df)
summary(m)


pdata <- df %>%
  select(TrainingMLSubtype, ends_with('WScore')) %>%
  pivot_longer(ends_with('WScore'))

ggplot(pdata, aes(x=name, y=value, fill=TrainingMLSubtype)) + 
  geom_boxplot()