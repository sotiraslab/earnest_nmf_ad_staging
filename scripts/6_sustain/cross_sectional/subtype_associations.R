
# === Imports ======

library(dplyr)
library(ggplot2)
library(stringr)
library(tibble)
library(tidyr)

# === Setup ======
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging'
path.master <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')

colors <- c(
  'Control' = 'gray',
  'S1' = '#db2b39',
  'S2' = '#053c5e',
  'S3' = '#f3a712' 
)

control.name <- 'Control'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'cross_sectional_associations')
dir.create(odir, showWarnings = F)

# === Load data ======

master <- read.csv(path.master)
master$TauLaterality <- abs(master$PTCLeftParietalTemporalWScore - master$PTCRightParietalTemporalWScore)
master$Subtype <- ifelse(df$ControlForStaging == "True", control.name, df$TrainingMLSubtype)

training <- master %>%
  filter(
    Split == 'TrainingBaseline',
    (ControlForStaging == "True") | (TrainingMLStage != 0 &  TrainingSubtypeValid ==1 )
  )

validation <- master %>%
  filter(
    Split == 'ValidationBaseline',
    (ControlForStaging == "True") | (TrainingMLStage != 0 &  TrainingSubtypeValid ==1 )
  )

# === Helper functions ======

my.anova <- function(x, y, data, correction='fdr', print = F) {
  fml <- as.formula(sprintf('%s ~ %s', y, x))
  anova <- aov(fml, data = data)
  posthoc <- as.data.frame(TukeyHSD(anova, method = correction)[[x]])
  posthoc.res <- posthoc %>%
    rownames_to_column('comparison') %>%
    mutate(annotation = cut(`p adj`,
                            breaks = c(0, 0.001, 0.01, 0.05, Inf),
                            labels = c('***', "**", "*", ""),
                            include.lowest = T)
    )
  if (print) {
    print(fml)
    print(summary(anova))
  }
  
  output <- list(anova = anova, posthoc = posthoc.res)
  return (output)
}

get_geom_sig_y_positions <- function(posthoc.res, ordered.x,
                                     start.pos = 1, gap = 1){
  
  # preprocessing
  posthoc.sig <- filter(posthoc.res, `p adj` < 0.05)
  comparisons <- str_split(posthoc.sig$comparison, '-')
  
  if (nrow(posthoc.sig) == 0) {
    return(NULL)
  }
  
  # data holders
  extents <- list()
  y_position <- rep(NA, nrow(posthoc.sig))
  
  # main loop
  for (i in seq_along(comparisons)){
    x <- comparisons[[i]]
    positions <- match(x, ordered.x)
    
    ypos <- NA
    check.pos <- start.pos
    while (is.na(ypos)) {
      
      # first iteration
      if (! as.character(check.pos) %in% names(extents)) {
        ypos <- check.pos
        extents[[as.character(check.pos)]] = sort(positions)
        next
      }
      
      # if entry already found, check if we can still fit new bar
      existing <- extents[[as.character(check.pos)]]
      if (max(existing) < min(positions)) {
        ypos <- check.pos
        both <- c(existing, positions)
        extents[[as.character(check.pos)]] = c(min(both), max(both))
      }
      check.pos <- check.pos + gap
    }
    
    # record found position
    y_position[i] <- ypos
  }
  
  return (y_position)
}

anova.plot <- function(x, y, data, colors, correction='fdr',
                       sig.y.start = 1, sig.y.gap = 1, y_lab = NULL) {
  
  # get anova stats
  anova.result <- my.anova(x = x, y = y, data = data, correction = correction, print = F)
  posthoc.res <- anova.result$posthoc
  posthoc.sig <- filter(posthoc.res, `p adj` < 0.05)
  comparisons <- str_split(posthoc.sig$comparison, '-')
  n.sig <- nrow(posthoc.sig)
  
  # get means by group
  n.categories <- length(unique(data[[x]]))
  means <- group_by(data, !!sym(x)) %>%
    summarise(Mean = mean(!!sym(y), na.rm=T)) %>%
    mutate(x=seq(0.5, by=1, length.out=n.categories),
           xend=seq(1.5, by=1, length.out=n.categories))
  
  # plot
  y_position = get_geom_sig_y_positions(posthoc.res = posthoc.res,
                                        ordered.x = sort(unique(data[[x]])),
                                        start.pos = sig.y.start,
                                        gap = sig.y.gap)
  
  ylab <- ifelse(is.null(y_lab), y, y_lab)
  p <- ggplot(data = data, aes(x = !!sym(x), y = !!sym(y), fill = !!sym(x))) +
    geom_point(position = position_jitter(width = 0.2, seed=42, height = 0), shape=21, size=3) +
    geom_segment(data=means, aes(x=x, xend=xend, y=Mean, yend=Mean),
                 color='black',
                 linewidth=1) + 
    scale_fill_manual(values=colors) +
    theme_light() +
    theme(legend.position = 'none',
          text = element_text(size=20)) +
    xlab(x) +
    ylab(ylab)
    
  if (! is.null(y_position)) {
    p <- p + geom_signif(
      comparisons=comparisons,
      annotations = posthoc.sig$annotation,
      y_position = y_position,
      tip_length = 0.01,
      size=.75,
      textsize = 7,
      vjust = 0.5)
  }
  print(p)
  
  output <- list(plot = p, anova = anova.result$anova, posthoc = posthoc.res)
  return (output)
    
}

pipeline <- function(split, y, sig.y.start = 1, sig.y.gap = 1, y_lab=NULL) {
  
  data <- list('training' = training, 'validation' = validation)[[split]]
  
  result <- anova.plot(x = 'Subtype', y = y, data = data, colors = colors,
                       correction = 'fdr', sig.y.start = sig.y.start,
                       sig.y.gap = sig.y.gap, y_lab = y_lab)
  
  # save stuff
  stub <- sprintf('%s_%s', y, split)
  
  # save plot
  
  pname <- sprintf('%s_swarmplot.svg', stub)
  ggsave(file.path(odir, pname), height = 6, width = 4, units = 'in')
  
  # save anova
  aname <- sprintf('%s_anova.csv', stub)
  anova <- result$anova
  anova.table <- summary(anova)[[1]]
  write.csv(anova.table, file.path(odir, aname), row.names = F)
  
  # save posthoc 
  sname <- sprintf('%s_posthoc.csv', stub)
  posthoc <- result$posthoc
  write.csv(posthoc, file.path(odir, sname), row.names = F)
}

# === Run ======

# Training
result <- pipeline('training', 'Age', sig.y.start = 92, sig.y.gap = 2)
result <- pipeline('training', 'Education', sig.y.start = 25, sig.y.gap = 2)
result <- pipeline('training', 'SummarySUVRAmyloid', sig.y.start = 2.25, sig.y.gap = .1, y_lab = 'Amyloid (SUVR)')
result <- pipeline('training', 'SummarySUVRTau', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Tau (SUVR)')
result <- pipeline('training', 'TauLaterality', sig.y.start = 10, sig.y.gap = 1, y_lab = 'Tau Laterality')
result <- pipeline('training', 'CDRSumBoxes', sig.y.start = 8, sig.y.gap = 1, y_lab = 'CDR (sum of boxes)')
result <- pipeline('training', 'MMSETotal', sig.y.start = 31, sig.y.gap = 1.2, y_lab = 'MMSE')

# Validation
result <- pipeline('validation', 'Age', sig.y.start = 92, sig.y.gap = 2)
result <- pipeline('validation', 'Education', sig.y.start = 22, sig.y.gap = 2)
result <- pipeline('validation', 'SummarySUVRAmyloid', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Amyloid (SUVR)')
result <- pipeline('validation', 'SummarySUVRTau', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Tau (SUVR)')
result <- pipeline('validation', 'TauLaterality', sig.y.start = 10, sig.y.gap = 1, y_lab = 'Tau Laterality')
result <- pipeline('validation', 'CDRSumBoxes', sig.y.start = 8, sig.y.gap = 1, y_lab = 'CDR (sum of boxes)')
result <- pipeline('validation', 'MMSETotal', sig.y.start = 31, sig.y.gap = 1.2, y_lab = 'MMSE')
