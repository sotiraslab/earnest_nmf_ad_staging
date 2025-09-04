
library(dplyr)
library(ggplot2)
library(jsonlite)
library(stringr)
library(tidyr)

ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

master.path <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
master <- read.csv(master.path)

pipeline <- function(split) {
  df <- master %>%
    filter(Split == split, ControlForStaging == 'False', TrainingMLStage != 0)
  
  samplesize <- nrow(df)
  name <- ifelse(str_detect(split, 'Training'), 'Training', 'Validation')
  key <- tolower(name)
  
  dependents.nice <- c(
    'PACParietal',
    'PACFrontal',
    'PACSensorimotor',
    'PACOccipital',
    'PTCMedialTemporal',
    'PTCRightParietalTemporal',
    'PTCLeftParietalTemporal',
    'PTCOccipital',
    'PTCFrontal',
    'PTCSensorimotor',
    'PTCInsularMedialFrontal'
  )
  dependents <- str_c(dependents.nice, 'WScore')
  n.dependents <- length(dependents)
  subtypes <- sort(unique(df$TrainingMLSubtype))
  n.subtypes <- length(subtypes)
  n.comparisons <- n.dependents * n.subtypes
  
  results <- matrix(NA, nrow = n.comparisons, ncol = 4)
  results <- as.data.frame(results)
  colnames(results) <- c('Subtype', 'Region', 't', 'p')
  
  index <- 1
  for (subtype in subtypes) {
    for (dependent in dependents) {
      data <- df
      data$Indicator <- df$TrainingMLSubtype == subtype
      fml <- as.formula(sprintf('%s ~ Indicator', dependent))
      m <- lm(fml, data = data)
      m.summary <- summary(m)
      t <- m.summary$coefficients[2, 3]
      p <- m.summary$coefficients[2, 4]
      
      results[index, 'Subtype'] <- subtype
      results[index, 'Region'] <- dependent
      results[index, 't'] <- t
      results[index, 'p'] <- p
      
      index <- index + 1
    }
  }
  
  
  results$p_adj <- p.adjust(results$p, method = 'fdr')
  results$annot <- cut(results$p_adj,
                       breaks = c(0, 0.001, 0.01, 0.05, Inf),
                       labels = c('***', '**', '*', ''),
                       include.lowest = T)
  results$Region <- str_replace(results$Region, 'WScore', '')
  results$Region <- factor(results$Region, levels = dependents.nice)
  
  # plot
  colors <- c(
    'S0' = 'gray',
    'S1' = '#db2b39',
    'S2' = '#053c5e',
    'S3' = '#f3a712' 
  )
  
  text.colors <- ifelse(str_detect(dependents, 'PAC'), '#1F4AD8', '#d41020')
  
 p <- ggplot(results, aes(x = Region, y = t, fill = Subtype)) + 
    geom_bar(stat = 'identity', position = position_dodge(), color = 'black') +
    theme_linedraw() +
    theme(
      text = element_text(size = 14),
      axis.text.x = element_text(angle = 45, hjust = 1, colour = text.colors),
    ) + 
    scale_fill_manual(values = colors) +
    geom_vline(xintercept = 4.5, linetype = 'dashed', color = 'gray') +
    ggtitle(sprintf('%s (n=%s)', name, samplesize))
 
 print(p)
 
 # save plot
 plot.path <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'ols', sprintf('%s_ols.svg', key))
 dir.create(dirname(plot.path), showWarnings = F, recursive = T)
 ggsave(plot.path, width = 8, height = 6, units = 'in')
 
 # save coefficients as JSON
 for (subtype in subtypes) {
   vals <- results[results$Subtype == subtype, 't']
   p <- results[results$Subtype == subtype, 'p_adj']
   vals <- ifelse(p < 0.05, vals, 0)
   names(vals) <- results[results$Subtype == subtype, 'Region']
   vals <- as.list(vals)
   
   out.json <- file.path(ROOT.OUTPUT, 'wta_json', sprintf('%s_%s_ols_coefficients.json', key, subtype))
   dir.create(dirname(out.json), showWarnings = F, recursive = T)
   write_json(vals, out.json, pretty = TRUE, auto_unbox = TRUE)
 }
 
 # return
 output <- list(
   plot = p,
   table = results
 )
 
 return(output)
}

out.train <- pipeline('TrainingBaseline')
out.validation <- pipeline('ValidationBaseline')

