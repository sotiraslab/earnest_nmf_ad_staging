
library(dplyr)
library(ggplot2)
library(stringr)
library(tibble)
library(tidyr)

ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging'

path.master <- file.path(ROOT.OUTPUT, 'filesForR', 'maindata.csv')
df <- read.csv(path.master)

colors <- list(A0T0 = 'white',
               A1T0 = '#5fabf7',
               A2T0 = '#1f4ad8',
               A2T1 = '#fee187',
               A2T2 = '#feab49',
               A2T3 = '#fc5b2e',
               A2T4 = '#d41020',
               Atypical = '#A661C9')

pipeline <- function(split, var, autosave = TRUE) {
  name <- if (split == 'TrainingBaseline') "Training" else "Validation"
  
  data <- df %>%
    filter(Split == split) %>%
    mutate(Stage = factor(Stage, levels = names(colors)))
  size <- nrow(data)
  
  # modeling
  fml <- as.formula(sprintf('%s ~ Stage', var))
  anova <- aov(fml, data = data)
  posthoc <- as.data.frame(TukeyHSD(anova, method='fdr')$Stage)
  print(summary(anova))
  
  # collect significant differences (from A0T0 stage)
  posthoc.res <- posthoc %>%
    rownames_to_column('comparison') %>%
    mutate(annotation = cut(`p adj`,
                            breaks = c(0, 0.001, 0.01, 0.05, Inf),
                            labels = c('***', "**", "*", ""),
                            include.lowest = T),
           a = str_extract(comparison, '[a-zA-Z0-9]+(?=-)'),
           b = str_extract(comparison, '(?<=-)[a-zA-Z0-9]+'),
           a = factor(a, levels = names(colors)),
           b = factor(b, levels = names(colors)),
           diff = round(diff, 2),
           lwr = round(lwr, 2),
           upr = round(upr, 2),
           `p adj` = round(`p adj`, 3),
           `p adj` = ifelse(`p adj` == 0, '<0.001', `p adj`)
    )
  
  if (var == 'CDRSumBoxes') {
    y <- -2
  } else if (var == 'MMSETotal') {
    y <- 31
  } else {
    y <- 1
  }
  posthoc.sig <- posthoc.res %>%
    filter(`p adj` < 0.05, b == 'A0T0') %>%
    mutate(y = y)
  
  # plot
  title <- sprintf("%s (n=%s)", name, size)
  if (var == 'CDRSumBoxes') {
    label <- 'CDR (sum of boxes)'
  } else if (var == 'MMSETotal') {
    label <- 'MMSE'
  } else {
    label <- var
  }
  p <- ggplot(data, aes(x=Stage, y=!!sym(var), fill=Stage)) +
    geom_boxplot(linewidth=.25, outlier.shape = 4, outlier.size = .25) +
    scale_fill_manual(values = colors) +
    geom_text(
      data = posthoc.sig,
      aes(x = a, y = y, label = annotation),
      inherit.aes = F,
      size=2) + 
    theme_bw() +
    theme(
      text = element_text(size = 8),
      legend.position = 'none',
      axis.text.x = element_text(angle = 30, vjust = 1, hjust = 1, color='black'),
      axis.text.y = element_text(color='black')) + 
    ylab(label)
  
  print(p)
  
  if (autosave) {
    
    odir <- file.path(ROOT.OUTPUT, 'plots', 'xsect_cognition')
    dir.create(odir, showWarnings = F, recursive = T)
    base <- sprintf('%s_%s', var, split)
    
    ggsave(file.path(odir, str_c(base, '.svg')), width = 2.5, height = 1.6, unit = 'in')
    write.csv(posthoc.res, file.path(odir, str_c(base, '.csv')), row.names = F)
  }
}

pipeline('TrainingBaseline', 'CDRSumBoxes')
pipeline('TrainingBaseline', 'MMSETotal')

pipeline('ValidationBaseline', 'CDRSumBoxes')
pipeline('ValidationBaseline', 'MMSETotal')


  