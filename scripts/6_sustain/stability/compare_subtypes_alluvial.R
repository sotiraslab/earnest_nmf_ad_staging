
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

# === Alluvial plot =====

my.alluvial <- function(split) {
  df <- master %>%
    filter(Split == split, ControlForStaging == 'False') %>%
    mutate(
      Training = ifelse(TrainingMLStage == 0, 'NS', TrainingMLSubtype),
      Validation =ifelse(ValidationMLStage == 0, 'NS', ValidationMLSubtype)
    ) 
  
  samplesize <- nrow(df)
  name <- ifelse(str_detect(split, 'Training'), 'Training', 'Validation')
  
  p.data <- df %>%
    select(Subject, Training, Validation) %>%
    pivot_longer(c('Training', 'Validation'), names_to = 'Model', values_to = 'Subtype') %>%
    mutate(
      Model = recode(Model, 'Training'='Discovery', 'Validation'='Replication'), 
      Model = factor(Model, levels=c('Discovery', 'Replication'))
    )
  
  colors <- c(
    'NS' = 'gray',
    'S1' = '#db2b39',
    'S2' = '#053c5e',
    'S3' = '#f3a712' 
  )
  
  p <- ggplot(p.data, aes(x = Model, stratum = Subtype, alluvium = Subject, fill = Subtype, label = Subtype)) +
    geom_flow(stat = "flow", aes.flow='forward') +
    geom_stratum(width=1/2) +
    theme_classic() +
    scale_y_continuous(expand = c(0, 0.005)) +
    scale_x_discrete(expand = c(0.13, 0.13)) +
    theme(
      axis.line.y = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.y = element_blank(),
      text = element_text(size = 6)
    ) + 
    scale_fill_manual(values = colors) +
    xlab('SuStaIn Model')
  
  print(p)
  
  return(p)
}

p <- my.alluvial('TrainingBaseline')
ggsave(file.path(odir, 'training_stability_alluvial.svg'), width = 2, height = 2, units = 'in')

p <- my.alluvial('ValidationBaseline')
ggsave(file.path(odir, 'validation_stability_alluvial.svg'), width = 2, height = 2, units = 'in')

# === Confusion matrix ======

# my.confmat <- function(split) {
#   df <- master %>%
#     filter(Split == split, ControlForStaging == 'False') %>%
#     mutate(
#       Training = ifelse(TrainingMLStage == 0 | TrainingSubtypeValid == 0, 'NA', TrainingMLSubtype),
#       Validation =ifelse(ValidationMLStage == 0 | ValidationSubtypeValid == 0, 'NA', ValidationMLSubtype)
#     )
#   
#   samplesize <- nrow(df)
#   name <- ifelse(str_detect(split, 'Training'), 'Training', 'Validation')
#   acc = round(mean(df$Training == df$Validation), 2)
#   ari = round(adjustedRandIndex(df$Training, df$Validation), 2)
#   
#   crosstab <- table(df$Training, df$Validation) %>%
#     as.data.frame() %>%
#     rename(Training=Var1, Validation=Var2) %>%
#     mutate(
#       Training = factor(Training, levels = c('S3', 'S2', 'S1', 'NA')),
#       Validation = factor(Validation, levels = c('NA', 'S1', 'S2', 'S3'))
#     )
#   
#   p <- ggplot(crosstab, aes(x=Validation, y=Training, fill=Freq, label = Freq)) + 
#     geom_tile(color='black', linewidth = 0.5) +
#     geom_text() + 
#     coord_fixed() +
#     scale_fill_colormap(colormap = c('#FFFFFF', '#4287f5'), reverse = T) +
#     scale_x_discrete(expand=c(0.13, 0.13)) + 
#     scale_y_discrete(expand=c(0.13, 0.13)) +
#     ggtitle(
#       sprintf('%s (n=%s)', name, samplesize),
#       subtitle = sprintf('Agreement=%s, ARI=%s', acc, ari)) +
#     ylab('Training SuStaIn') +
#     xlab('Validation SuStaIn') +
#     theme(
#       text = element_text(size = 14),
#       panel.background = element_rect(fill = "white"), 
#       panel.grid.major = element_blank(),             
#       panel.grid.minor = element_blank()
#       )              
#   
#   print(p)
#   
#   return (p)
# }
# 
# p <- my.confmat('TrainingBaseline')
# ggsave(file.path(odir, 'training_stability_confmat.svg'), width = 6, height = 6, units = 'in')
# 
# p <- my.confmat('ValidationBaseline')
# ggsave(file.path(odir, 'validation_stability_confmat.svg'), width = 6, height = 6, units = 'in')