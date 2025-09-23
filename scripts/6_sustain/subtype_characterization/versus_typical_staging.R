library(dplyr)
library(ggalluvial)
library(ggplot2)
library(lubridate)
library(stringr)
library(this.path)
library(tidyr)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

# Load data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA)
master$Subtype <- factor(master$TrainingMLSubtype, levels = c('S1', 'S2', 'S3'))
master$ATStage <- master$Stage

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'sustain_vs_atstaging')
dir.create(odir, showWarnings = F)

# Load plot script
path.script <- normalizePath(file.path(this.dir(), '..', '..', 'rsource', 'stacked_barplot.R'))
source(path.script)

# data selection
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

# Plot

pipeline <- function(data, name) {
  
  atcolors <- list(
    A0T0 = 'white',
    A1T0 = '#5fabf7',
    A2T0 = '#1f4ad8',
    A2T1 = '#fee187',
    A2T2 = '#feab49',
    A2T3 = '#fc5b2e',
    A2T4 = '#d41020',
    Atypical = '#A661C9',
    'Other'= 'gray',
    'A0T+'= '#c6c7e1',
    'A1T+'= '#796eb2',
    'MTL-'= '#3f007d'
  )
  
  scolors <- list(
    'NA' = 'gray',
    'S1' = '#db2b39',
    'S2' = '#053c5e',
    'S3' = '#f3a712' 
  )
  
  atcolors <- unlist(atcolors)
  scolors <- unlist(scolors)
  colors <- c(atcolors, scolors)
  
  # Alluvial plot
  p.data <- data %>%
    select(Subject, Subtype, ATStage) %>%
    pivot_longer(-Subject, names_to = 'Model', values_to = 'Label') %>%
    mutate(
      Model = factor(Model, levels = c('ATStage', 'Subtype'))
    )
  
  ggplot(data = p.data, aes(x = Model, stratum = Label, alluvium = Subject, fill = Label, label = Label)) +
    geom_flow(stat = "flow", aes.flow='forward') +
    geom_stratum(width=1/2) +
    theme_classic() +
    scale_y_continuous(expand = c(0, 0.005)) +
    scale_x_discrete(expand = c(0.13, 0.13)) +
    theme(
      axis.line.y = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.y = element_blank(),
      text = element_text(size = 14)
    ) +
    scale_fill_manual(values = colors)
  
  ggsave(file.path(odir, sprintf('%s_alluvial_comparison.svg', name)), width = 6, height = 8, units = 'in')
  
  # Stacked bar 
  stacked.barplot(
    df = data,
    xcol = 'Subtype',
    ycol = 'ATStage',
    colors = atcolors,
    annotate = T,
    annotate.size = 5,
    annotation.minsize = 2)
  
  ggsave(file.path(odir, sprintf('%s_barplot_atstage.svg', name)), width = 6, height = 8, units = 'in')
  
  # Show atypical cases
  atypical <- data %>%
    filter(ATStage == 'Atypical')
  
  stacked.barplot(
    df = atypical,
    xcol = 'StageLabelNS',
    ycol = 'Subtype',
    colors = colors,
    annotate = T,
    annotate.color = 'white',
    annotate.size = 5
  ) + ylab('Atypical Stage')
  
  ggsave(file.path(odir, sprintf('%s_barplot_atypical.svg', name)), width = 6, height = 8, units = 'in')
  
}

pipeline(training, 'training')
pipeline(validation, 'validation')
