library(dplyr)
library(emmeans)
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

pipeline <- function(split) {
  
  data <- if (split == 'training') training else validation
  odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'tau_v_amyloid', 'training')
  dir.create(odir, showWarnings = F)
    
  plots <- vector(mode = 'list', length = length(ptcs))
  tcompare <- as.data.frame(matrix(NA, nrow = 3 * length(ptcs), ncol = 4))
  
  colors <- c(
    'NA' = 'gray',
    'S1' = '#db2b39',
    'S2' = '#053c5e',
    'S3' = '#f3a712' 
  )
  
  for (i in 1:length(ptcs)) {
    # plot
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
    
    # save plot
    savename <- sprintf('%s.svg', ptc)
    ggsave(file.path(odir, savename), width = 8, height = 8, units='in')
    
    # model
    fml <- as.formula(paste(ptc, '~', 'SummarySUVRAmyloid', '*', 'Subtype'))
    m <- lm(fml, data=data)
    em <- emmeans(m, 'Subtype')
    em.summary <- summary(pairs(em, adjust='fdr', reverse=T))
    
    a <- ((i-1) * 3) + 1
    b <- a + 2
    tcompare[a:b, 1] <- ptc
    tcompare[a:b, 2] <- em.summary$contrast
    tcompare[a:b, 3] <- em.summary$t.ratio
    tcompare[a:b, 4] <- em.summary$p.value
  }
  
  # Post-processing of the t-comparisons
  colnames(tcompare) <- c('PTC', 'contrast', 't.ratio', 'p.value')
  tcompare <- tcompare %>%
    mutate(
      p.adjust = p.adjust(p.value, method='fdr'),
      annotation = cut(p.adjust,
                       breaks = c(0, 0.001, 0.01, 0.05, Inf),
                       labels = c('***', "**", "*", ""),
                       include.lowest = T),
      t.adjust = ifelse(p.adjust < 0.05, t.ratio, NA),
      across(where(is.numeric), round, 3),
      p.value = ifelse(p.value == 0, '<0.001', p.value),
      p.adjust = ifelse(p.adjust == 0, '<0.001', p.value)
      )
  
  # save tcomparisons
  write.csv(tcompare, file.path(odir, 'tcompare.csv'), row.names = F)
  
  # Create JSON for WTA image
  for (contrast in unique(tcompare$contrast)) {
    subset <- tcompare[tcompare$contrast == contrast, ]
    vals <- subset$t.adjust
    names(vals) <- str_replace(subset$PTC, 'WScore', '')
    vals.list <- as.list(vals)
    
    wta.dir <- file.path(ROOT.OUTPUT, 'wta_json', 'tau_v_amyloid_by_subtype')
    dir.create(wta.dir, showWarnings = F)
    savename <- sprintf('%s_tau-v-amyloid_%s.json', split, str_replace(contrast, ' - ', ''))
    write_json(vals.list, file.path(wta.dir, savename), pretty = TRUE, auto_unbox = TRUE, na = 'null')
  }
  
  # Show plot
  p <- ggarrange(plotlist = plots, common.legend = TRUE, legend="top", labels = NULL)
  print(p)
  
  # Collect results
  result <- list(
    plot = p,
    tcompare = tcompare
  )
  return (result)
}


result.train <- pipeline('training')
result.val <- pipeline('validation')