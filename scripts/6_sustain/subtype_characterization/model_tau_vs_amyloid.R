library(dplyr)
library(ggplot2)
library(ggpubr)
library(jsonlite)
library(stringr)
library(tidyr)

ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'tau_v_amyloid')
dir.create(odir, showWarnings = F)

master.path <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
master <- read.csv(master.path)

ptcs <- colnames(master)[str_detect(colnames(master), 'PTC.*WScore')]

training <- master %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False', TrainingMLStage != 0, TrainingSubtypeValid == 1) %>%
  mutate(Subtype = TrainingMLSubtype)

validation <- master %>%
  filter(Split == 'ValidationBaseline', ControlForStaging == 'False', TrainingMLStage != 0, TrainingSubtypeValid == 1) %>%
  mutate(Subtype = TrainingMLSubtype)

pipeline <- function(data) {
  plots <- vector(mode = 'list', length = length(pacs))
  
  colors <- c(
    'NA' = 'gray',
    'S1' = '#db2b39',
    'S2' = '#053c5e',
    'S3' = '#f3a712' 
  )
  
  for (i in 1:length(ptcs)) {
    ptc <- ptcs[i]
    title <- ptc %>% str_replace('WScore', '') %>% str_replace('PTC', 'PTC-')
    p <- ggplot(data=data, aes(x = SummarySUVRAmyloid, y = !!sym(ptc), color = Subtype)) +
      geom_smooth(method = 'lm') +
      coord_cartesian(ylim = c(0, 20)) +
      theme_bw() +
      scale_color_manual(values = colors) +
      theme(text = element_text(size = 12), plot.title = element_text(size = 12)) + 
      ggtitle(title) +
      ylab('W') +
      xlab('Amyloid (SUVR)')
    plots[[i]] <- p
  }
  
  p <- ggarrange(plotlist = plots, common.legend = TRUE, legend="top", labels = NULL)
  print(p)
  return (p)
}


p <- pipeline(training)
ggsave(file.path(odir, 'training_tau_v_amyloid.svg'), width = 8, height = 8, units = "in", dpi = 300)

p <- pipeline(validation)
ggsave(file.path(odir, 'validation_tau_v_amyloid.svg'), width = 8, height = 8, units = "in", dpi = 300)

# m <- lm(PTCOccipitalWScore ~ SummarySUVRAmyloid*Subtype, data=training)
# summary(m)
# em <- emmeans(m, 'Subtype')
# em.summary <- summary(pairs(em, adjust='fdr')) %>%
#   mutate(across(where(is.numeric), function(x) round(x, 3)),
#          annotation = cut(p.value,
#                           breaks = c(0, 0.001, 0.01, 0.05, Inf),
#                           labels = c('***', "**", "*", ""),
#                           include.lowest = T)) %>%
#   select(-df, -SE)