
# === Imports ======
library(dplyr)
library(emmeans)
library(ggalluvial)
library(ggplot2)
library(lubridate)
library(stringr)
library(this.path)
library(tidyr)

# === Setup ======

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'stage_regression')
dir.create(odir, showWarnings = F)

# === Data loading ======

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

validation <- master %>%
  filter(
    Split == 'ValidationBaseline',
    ControlForStaging == "False",
    TrainingMLStage != 0,
    TrainingSubtypeValid ==1
  )

# === Helper func ====== 
# data <- training
# dependent <- 'SummarySUVRTau'
# ylab <- 'Tau (SUVR)'
# annot.xpos <- 'left'
# annot.ypos <- 'top'

pipeline <- function(split, dependent, ylab = NULL, save = TRUE) {
  data <-  if(split == 'training') training else validation
  
  # model
  fml <- as.formula(sprintf('%s ~ Stage * Subtype', dependent))
  m <- lm(fml, data=data)
  m.summary <- summary(m)
  em <- emmeans(m, 'Subtype')
  em.pairs <- summary(pairs(em, adjust='fdr'))
  
  # pull out results
  r2 <- m.summary$r.squared
  f <- m.summary$fstatistic
  p <- pf(f[1],f[2],f[3],lower.tail=F)
  
  # plot
  colors <- c(
    'Control' = 'gray',
    'S1' = '#db2b39',
    'S2' = '#053c5e',
    'S3' = '#f3a712' 
  )
  
  rround <- round(r2, 3)
  if (p < 0.001) {
    ptext <- 'p<0.001'
  } else {
    ptext <- sprintf('p=%s',round(p, 3))
  }
  
  ylab <- if(is.null(ylab)) dependent else ylab
  
  p <- ggplot(data = training, aes(x = Stage, y = !!sym(dependent), fill = Subtype, color=Subtype)) +
    geom_point(position = position_jitter(), alpha = 0.3, shape=19) +
    geom_smooth(method = 'lm') + 
    scale_fill_manual(values = colors) +
    scale_color_manual(values = colors) +
    theme(text = element_text(size = 14)) +
    theme_light() +
    scale_x_continuous(breaks = 1:11) +
    ggtitle(
      bquote(R^2 * '=' * .(rround) * ', ' * .(ptext))
    ) +
    ylab(ylab) + 
    xlab('SuStaIn Stage')
  
  print(p)
  
  # save plot
  if (save) {
    opath <- file.path(odir, sprintf('%s_%s.svg', dependent, split))
    ggsave(opath, width = 6, height = 6, units = 'in')
    
    # save model
    opath <- file.path(odir, sprintf('%s_%s.txt', dependent, split))
    sink(opath)
    print(m.summary)
    sink()
    
    # save posthoc
    opath <- file.path(odir, sprintf('%s_%s.csv', dependent, split))
    write.csv(em.pairs, opath, row.names = F)
  }
}

# ==== Run =======

pipeline('training', 'SummarySUVRAmyloid', 'Amyloid (SUVR)')
pipeline('training', 'SummarySUVRTau', 'Tau (SUVR)')
pipeline('training', 'MMSETotal', 'MMSE')
pipeline('training', 'CDRSumBoxes', 'CDR (sum of boxes)')
pipeline('training', 'Age')

pipeline('validation', 'SummarySUVRAmyloid', 'Amyloid (SUVR)')
pipeline('validation', 'SummarySUVRTau', 'Tau (SUVR)')
pipeline('validation', 'MMSETotal', 'MMSE')
pipeline('validation', 'CDRSumBoxes', 'CDR (sum of boxes)')
pipeline('validation', 'Age')
