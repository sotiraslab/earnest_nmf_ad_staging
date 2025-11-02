library(dplyr)
library(ggplot2)
library(gt)
library(gtsummary)
library(lubridate)
library(stringr)
library(this.path)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'
MUSE.VALUES <- '/Users/earnestt1234/Desktop/_muse_tau.csv'
MUSE.ROIS <- '/Users/earnestt1234/Desktop/muse_rois_clean.csv'
PATH.STATSFUNCS <- normalizePath(file.path(this.dir(), '..', '..', '..', 'rsource', 'statsfuncs.R'))
source(PATH.STATSFUNCS)

# Load main data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_clinical_stages.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA) %>%
  filter(AA2024Clinical != '',
         ResilientVulnerable %in% c('Expected', 'Vulnerable', 'Resilient')) %>%
  mutate(ResilientVulnerable = factor(ResilientVulnerable))

# Load muse
muse.rois <- read.csv(MUSE.ROIS)
muse.values <- read.csv(MUSE.VALUES)

volume.regions <- muse.rois[muse.rois$TissueType == 'GM' & muse.rois$IsCerebellum == 'False', 'Name']
volume.region.cols <- str_c(volume.regions, '_VOLUME')
vols <- muse.values[, volume.region.cols] %>%
  dplyr::select(-contains('cerebral_exterior'))
total_volume <- rowSums(vols)
volume.merger <- muse.values[, c('Subject', 'Session')]
volume.merger$GMVolume <- total_volume

master_with_vol <- left_join(master, volume.merger, by = c('Subject', 'Session'))

# ICV normalization
master_with_vol$GMVolume <- master_with_vol$GMVolume / master_with_vol$ICV

# remove cases with MRI not acquired near PET
master_with_vol <- master_with_vol %>%
  mutate(T1Gap = abs(difftime(ymd_hms(TauAmyloidMeanDate), ymd(ScanDateT1), units='days')),
         GMVolume = ifelse(T1Gap > 366, NA, GMVolume))

training <- master_with_vol %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False')
validation <- master_with_vol %>%
  filter(Split == 'ValidationBaseline', ControlForStaging == 'False')

# ====== Model ==========

pipeline <- function(data) {
  dependents <- c(
    'Age', 'SexMale', 'Education', 'BMI', "HasE4", 'MMSETotal', 'CDRSumBoxes',
    'GMVolume', 'SummarySUVRAmyloid', 'SummarySUVRTau'
  )
  binary.dependents <- c('SexMale', 'HasE4')
  
  result.rows <- vector(mode = 'list', length = length(dependents))
  
  for (i in 1:length(dependents)) {
    dependent <- dependents[i]
    
    if (dependent %in% binary.dependents) {
      result.rows[[i]] <- run.chisq.binary.dependent(
        dependent = dependent,
        independent = 'ResilientVulnerable',
        data = data
      )
    } else {
      result.rows[[i]] <- run.ancova(
        dependent = dependent,
        independent = 'ResilientVulnerable',
        covariates = c('Age', 'SexMale'),
        data = data
      )
    }
  }
  
  result <- bind_rows(result.rows)
  
  # include multiple comparisons adjustment
  pair.cols <- colnames(result)[str_detect(colnames(result), ' vs. ')]
  id.cols <- colnames(result)[! colnames(result) %in% pair.cols]
  result.star <- result %>%
    mutate(across(all_of(pair.cols), function (x) ifelse(p < 0.05, x, NA))) %>%
    pivot_longer(all_of(pair.cols), names_to = 'Comparison', values_to = 'comp_p') %>%
    mutate(comp_p_adj = p.adjust(comp_p, method = 'fdr'),
           annot = as.character(cut(comp_p_adj,
                                    breaks = c(0, 0.001, 0.01, 0.05, Inf),
                                    labels = c('***', "**", "*", ""),
                                    include.lowest = T)),
           annot = ifelse(is.na(annot), '', annot),
           annot = str_c(ifelse(comp_p_adj < 0.001, '<0.001', round(comp_p_adj, 3)), annot),
           p = round(p, 3),
           p = ifelse(p < 0.001, '<0.001', p)
    )  %>%
    pivot_wider(id_cols = all_of(id.cols), names_from = Comparison, values_from = annot)
  
  return (result.star)
}

train.result <- pipeline(training)
validation.result <- pipeline(validation)

odir <- file.path(ROOT.OUTPUT, 'tables')
dir.create(odir, showWarnings = F)
write.csv(train.result, file.path(odir, 'training_resilient_vulnerable_models.csv'), row.names = F)
write.csv(validation.result, file.path(odir, 'validation_resilient_vulnerable_models.csv'), row.names = F)

# ====== Show distribution by data set =======

PLOT.DIR <- file.path(ROOT.OUTPUT, 'plots', 'resilient_v_vulnerable')
dir.create(PLOT.DIR, showWarnings = F)

stacked.barplot <- function(df, xcol, ycol, levels=NULL, colors=NULL,
                            return.data = F, dropna = F) {
  
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
  
  if (! is.null(colors)) {
    p <- p + scale_fill_manual(values=colors)
  }
  
  print(p)
  
  return(p)
}

colors <- list(A0T0 = 'white',
               A1T0 = '#5fabf7',
               A2T0 = '#1f4ad8',
               A2T1 = '#fee187',
               A2T2 = '#feab49',
               A2T3 = '#fc5b2e',
               A2T4 = '#d41020',
               Atypical = '#A661C9',
               NS = '#c6c7e1',
               'A0T+' = '#796eb2',
               'A1T+' = '#3f007d')

p <- stacked.barplot(training, xcol = 'ResilientVulnerable', ycol = 'Stage', colors=colors) +
  xlab("Status")
ggsave(file.path(PLOT.DIR, 'training_stage_distribution.svg'), width = 7, height = 7, unit = 'in')

p <- stacked.barplot(validation, xcol = 'ResilientVulnerable', ycol = 'Stage', colors=colors) +
  xlab("Status")
ggsave(file.path(PLOT.DIR, 'validation_stage_distribution.svg'), width = 7, height = 7, unit = 'in')
