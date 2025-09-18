# ===== Imports =====
library(dplyr)
library(ggplot2)
library(lubridate)
library(stringr)
library(tidyr)

# ===== Config =====

# Set configuration
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'stability')
dir.create(odir, showWarnings = F)

colors <- c(
  'NA' = 'gray',
  'S1' = '#db2b39',
  'S2' = '#053c5e',
  'S3' = '#f3a712' 
)

# ===== Load Data =====

master.path <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
master <- read.csv(master.path)

# training
tmp <- master %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False', TrainingMLStage != 0, TrainingSubtypeValid == 1)
training.subs <- tmp$Subject

training <- master %>%
  filter(Subject %in% training.subs)

# validation
tmp <- master %>%
  filter(Split == 'ValidationBaseline', ControlForStaging == 'False', TrainingMLStage != 0, TrainingSubtypeValid == 1)
validation.subs <- tmp$Subject

validation <- master %>%
  filter(Subject %in% validation.subs)

# ===== Subtypes over time =====

stacked.barplot <- function(df, xcol, ycol, levels=NULL, colors=NULL,
                            return.data = F, dropna = F, annotate = F,
                            annotate.color = 'black') {
  
  # create data
  if (dropna) {
    df <- df[! is.na(df[[xcol]]), ]
    df <- df[! is.na(df[[ycol]]), ]
  }
  
  plot.data <- df %>%
    group_by_at(c(xcol, ycol)) %>%
    summarise(N=n())
  
  if (! is.null(levels)) {
    plot.data <- filter(plot.data, !!sym(xcol) %in% levels)
  }
  plot.data <- plot.data %>%
    ungroup() %>%
    group_by(!!sym(xcol)) %>%
    mutate(Percent = N / sum(N) * 100)
  
  if (return.data) {
    return (plot.data)
  }
  
  # annotations
  x.order <- unique(plot.data[[xcol]])
  y.order <- unique(plot.data[[ycol]])
  annot.data <- plot.data %>%
    mutate(XFactor = factor(!!sym(xcol), levels = x.order),
           YFactor = factor(!!sym(ycol), levels = rev(y.order))) %>%
    arrange(XFactor, YFactor) %>%
    mutate(AnnotX = as.integer(XFactor)) %>%
    group_by(XFactor) %>%
    mutate(AnnotYMax = cumsum(Percent),
           AnnotYMin = AnnotYMax - Percent,
           AnnotY = (AnnotYMin + AnnotYMax) / 2,
           Annot = str_c(round(Percent, 2), '%'))
  
  # get totals for text
  group.sums <- plot.data %>%
    group_by(!!sym(xcol)) %>%
    summarise(total=sum(N)) %>%
    ungroup()
  
  # plot
  p <- ggplot() +
    geom_bar(data = plot.data, aes(fill=!!sym(ycol), y=Percent, x=!!sym(xcol)), stat="identity", color='black') +
    geom_text(data = group.sums, aes(x=!!sym(xcol), y=105, label=total), size=6) +
    theme_classic() +
    ylab('Observations (%)') +
    xlab(xcol) +
    scale_y_continuous(expand=expansion(mult=c(0, .1)), breaks = c(0, 25, 50, 75, 100)) +
    guides(fill=guide_legend(title=ycol)) +
    theme(text = element_text(size=20),
          axis.line.y = element_blank()) +
    geom_segment(aes(y=0,yend=100,x=-Inf,xend=-Inf), color='black', linewidth=1)
  
  if (annotate) {
    p <- p + geom_text(
      data = annot.data,
      aes(x = AnnotX, y = AnnotY, label = Annot),
      inherit.aes = F,
      color = annotate.color,
      size = 6)
  }
  
  if (! is.null(colors)) {
    p <- p + scale_fill_manual(values=colors)
  }
  
  return(p)
}

subtypes.over.time <- function(data) {
  p.data <- data %>%
    group_by(Subject) %>%
    filter(n() >= 2) %>%
    summarise(
      Baseline = first(TrainingMLSubtype),
      Followup = last(TrainingMLSubtype),
      FollowupStage = last(TrainingMLStage),
      FollowupValid = last(TrainingSubtypeValid)
      ) %>%
    ungroup() %>%
    mutate(Followup = ifelse(FollowupStage == 0 | FollowupValid == 'False', 'NA', Followup))
  
  stacked.barplot(p.data, xcol='Baseline', ycol='Followup', colors = colors, annotate = T, annotate.color = 'white')
}

subtypes.over.time(training)
ggsave(file.path(odir, 'longitudinal_subtypes_training.svg'), width = 6, height = 6, units = "in", dpi = 300)

subtypes.over.time(validation)
ggsave(file.path(odir, 'longitudinal_subtypes_validation.svg'), width = 6, height = 6, units = "in", dpi = 300)

# ===== Stages over time =====

stages.over.time <- function(data) {
  p.data <- data %>%
    group_by(Subject) %>%
    filter(n() >= 2) %>%
    summarise(Baseline = first(TrainingMLStage),
              Followup = last(TrainingMLStage),
              Subtype = first(TrainingMLSubtype),
    ) %>%
    ungroup() %>%
    pivot_longer(-c(Subject, Subtype), names_to = 'Visit', values_to = 'Stage')
  
  # statistics
  subtypes <- c('S1', 'S2', 'S3')
  rows <- vector(mode = 'list', length = length(subtypes))
  for (i in 1:length(subtypes)) {
    subtype <- subtypes[i]
    x <- unname(unlist(p.data[p.data$Subtype == subtype & p.data$Visit == 'Baseline', 'Stage']))
    y <- unname(unlist(p.data[p.data$Subtype == subtype & p.data$Visit == 'Followup', 'Stage']))
    test <- t.test(x = x, y = y, paired = T)
    tres <- list(Subtype=subtype, t=test$statistic, p=test$p.value, x=i)
    rows[[i]] <- tres
  }
  
  t.df <- bind_rows(rows) %>%
    mutate(
      p_adj = p.adjust(p, method = 'fdr'),
      annotation = cut(p_adj,
                       breaks = c(0, 0.001, 0.01, 0.05, Inf),
                       labels = c('***', "**", "*", "NS"),
                       include.lowest = T),
      xmin = x - .2,
      xmax = x + .2
    )
  
  ggplot(p.data, aes(x=Subtype, y=Stage, fill=Visit)) +
    geom_boxplot() +
    theme_bw() +
    theme(text = element_text(size = 14),
          axis.text.x = element_text(color = c(colors[['S1']], colors[['S2']], colors[['S3']]))) +
    scale_fill_manual(values = c('Baseline'='azure2', 'Followup'='azure4')) +
    geom_signif(
      y_position = c(11.5, 11.5, 11.5),
      xmin = t.df$xmin,
      xmax = t.df$xmax,
      annotation = t.df$annotation,
      tip_length = 0,
      size = 0.5,
      textsize = 5
    ) +
    scale_y_continuous(breaks = c(1, 3, 5, 7, 9, 11))
}


stages.over.time(training)
ggsave(file.path(odir, 'longitudinal_stages_training.svg'), width = 6, height = 6, units = "in", dpi = 300)

stages.over.time(validation)
ggsave(file.path(odir, 'longitudinal_stages_validation.svg'), width = 6, height = 6, units = "in", dpi = 300)