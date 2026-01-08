
library(colormap)
library(dplyr)
library(ggalluvial)
library(ggplot2)
library(mclust)
library(stringr)
library(tidyr)

ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

master.path <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
master <- read.csv(master.path)

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'stability')
dir.create(odir, showWarnings = F, recursive = T)

train <- master %>%
  filter(Split == 'TrainingBaseline',
         ControlForStaging == 'False',
         TrainingSubtypeValid == 1,
         TrainingMLStage > 0,
         CDRBinned != '') %>%
  mutate(Stage = factor(TrainingMLStage, levels=1:11))

validation <- master %>%
  filter(Split == 'ValidationBaseline',
         ControlForStaging == 'False',
         TrainingSubtypeValid == 1,
         TrainingMLStage > 0,
         CDRBinned != '') %>%
  mutate(Stage = factor(TrainingMLStage, levels=1:11))

# Helper function
# Copying rather than sourcing b/c needed to make multiple sizing changes
my.plot <- function(x, y, data, colors=NULL, do.anova=F, correction='fdr',
                       sig.y.start = 1, sig.y.gap = 1, y_lab = NULL) {
  
  # get means by group
  n.categories <- length(unique(data[[x]]))
  means <- group_by(data, !!sym(x)) %>%
    summarise(Mean = mean(!!sym(y), na.rm=T)) %>%
    mutate(x=seq(0.5, by=1, length.out=n.categories),
           xend=seq(1.5, by=1, length.out=n.categories))
  
  # plot
  ylab <- ifelse(is.null(y_lab), y, y_lab)
  p <- ggplot(data = data, aes(x = !!sym(x), y = !!sym(y), fill = !!sym(x))) +
    geom_point(
      position = position_jitter(width = 0.2, seed=42, height = 0),
      shape=21, size=1, stroke=.2) +
    geom_segment(data=means, aes(x=x, xend=xend, y=Mean, yend=Mean),
                 color='black',
                 linewidth=.4) + 
    theme_bw() +
    theme(legend.position = 'none',
          text = element_text(size=20)) +
    xlab(x) +
    ylab(ylab)
  
  if (! is.null(colors)) {
    p <- p + scale_fill_manual(values = colors)
  }
  
  p
  
}

# CDR - Training =====
p <- my.plot(
  'CDRBinned', 'TrainingProbMLSubtype', train,
  sig.y.start = 1.01, sig.y.gap = .05, do.anova = F,
  colors=colormap('YIGnBu', nshades = 3, reverse = T)
) +
  ylab('P(Subtype)') +
  xlab('CDR Global') +
  coord_cartesian(ylim=c(0,1)) +
  theme(text = element_text(size=6))
p

ggsave(file.path(odir, 'training_prob_v_cdr.svg'), width = 1.5, height=2, units='in')

# SustainStage - Training =====
p <- my.plot(
  'Stage', 'TrainingProbMLSubtype', train,
  sig.y.start = 1.01, sig.y.gap = .05, do.anova = F,
  colors=colormap('YIOrRd', nshades = 11, reverse = T)
  ) +
  ylab('P(Subtype)') +
  xlab('SuStaIn Stage') +
  coord_cartesian(ylim=c(0,1)) +
  theme(text = element_text(size=6))
p

ggsave(file.path(odir, 'training_prob_v_stage.svg'), width = 2, height=2, units='in')

# By subtype - Training =====
p <- my.plot(
  'TrainingMLSubtype', 'TrainingProbMLSubtype', train,
  sig.y.start = 1.01, sig.y.gap = .05, do.anova = F,
  colors=c('#db2b39', '#053c5e','#f3a712')
) +
  ylab('P(Subtype)') +
  xlab('Subtype') +
  coord_cartesian(ylim=c(0,1)) +
  theme(text = element_text(size=6))
p

ggsave(file.path(odir, 'training_prob_v_subtype.svg'), width = 1.5, height=2, units='in')

# CDR - Validation =====
p <- my.plot(
  'CDRBinned', 'TrainingProbMLSubtype', validation,
  sig.y.start = 1.01, sig.y.gap = .05, do.anova = F,
  colors=colormap('YIGnBu', nshades = 3, reverse = T)
) +
  ylab('P(Subtype)') +
  xlab('CDR Global') +
  coord_cartesian(ylim=c(0,1)) +
  theme(text = element_text(size=6))
p

ggsave(file.path(odir, 'validation_prob_v_cdr.svg'), width = 1.5, height=2, units='in')

# SustainStage - Validation =====
p <- my.plot(
  'Stage', 'TrainingProbMLSubtype', validation,
  sig.y.start = 1.01, sig.y.gap = .05, do.anova = F,
  colors=colormap('YIOrRd', nshades = 11, reverse = T)
) +
  ylab('P(Subtype)') +
  xlab('SuStaIn Stage') +
  coord_cartesian(ylim=c(0,1)) +
  theme(text = element_text(size=6))
p

ggsave(file.path(odir, 'validation_prob_v_stage.svg'), width = 2, height=2, units='in')

# By subtype - Training =====
p <- my.plot(
  'TrainingMLSubtype', 'TrainingProbMLSubtype', validation,
  sig.y.start = 1.01, sig.y.gap = .05, do.anova = F,
  colors=c('#db2b39', '#053c5e','#f3a712')
) +
  ylab('P(Subtype)') +
  xlab('Subtype') +
  coord_cartesian(ylim=c(0,1)) +
  theme(text = element_text(size=6))
p

ggsave(file.path(odir, 'validation_prob_v_subtype.svg'), width = 1.5, height=2, units='in')
