
# === Imports ======

library(dplyr)
library(ggplot2)
library(stringr)
library(this.path)
library(tibble)
library(tidyr)

# === Setup ======
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging'
path.master <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_nps.csv')
path.braak <- file.path(ROOT.OUTPUT, 'filesForR', 'braak_wscores.csv')

colors <- c(
  'Control' = 'gray',
  'S1' = '#db2b39',
  'S2' = '#053c5e',
  'S3' = '#f3a712' 
)

control.name <- 'Control'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'cross_sectional_associations')
dir.create(odir, showWarnings = F)

# === Load ANOVA helper funcs ======

path.anova <- '../../rsource/anova.R'
source(path.anova)

path.barplot <- '../../rsource/stacked_barplot.R'
source(path.barplot)

# === Load data ======

master <- read.csv(path.master)
master$TauLaterality <- abs(master$PTCLeftParietalTemporalWScore - master$PTCRightParietalTemporalWScore)
master$Subtype <- ifelse(master$ControlForStaging == "True", control.name, master$TrainingMLSubtype)

composites <- c('CompositeMEM', 'CompositeEXF', 'CompositeLAN', 'CompositeVSP')
master <- master %>%
  mutate(
    across(all_of(composites), function(x) ifelse(is.infinite(x), NA, x))
    )

braak <- read.csv(path.braak)
master <- left_join(master, braak, by=c('Subject', 'Session'))
master <- master %>%
  mutate(AAStage = AA2024BiologicalStage,
         AAStage = recode(
           AAStage,
           "Atypical" = 'MTL-',
           "$A+/T_{2}-$" = 'A+/T-',
           "$A+/T_{2MTL}+$" = 'A+/MTL+',
           "$A+/T_{2MOD}+$" = 'A+/NEO+',
           "$A+/T_{2HIGH+}$" = 'A+/NEO++',
           `0` = 'A-/T-'
           ),
         AAStage = ifelse(FinalAmyloidStatus == 1 & AAStage == 'A-/T-', 'A+/T-', AAStage), 
         AAStage = factor(
           AAStage,
           levels = c('A-/T-', 'A+/T-', 'A+/MTL+', 'A+/NEO+', 'A+/NEO++', 'MTL-')
           )
         )

# # residualize composites
# master$CompositeGLO <- (
#   master$CompositeMEM + master$CompositeEXF + master$CompositeLAN + master$CompositeVSP
# ) / 4
# 
# nps.present <- master %>% drop_na(all_of(composites))
# nps.resid <- nps.present[, c('Subject', 'Session')]
# for (col in composites) {
#   dest <- sprintf('%sResidualized', col)
#   fml <- as.formula(sprintf('%s ~ SummarySUVRAmyloid', col))
#   m <- lm(fml, data = nps.present)
#   nps.resid[[dest]] <- m$residuals
# }
# 
# master <- left_join(master, nps.resid, by = c('Subject', 'Session'))

# ==== Split Data ========
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

# === Helper functions ======

pipeline <- function(split, y, sig.y.start = 1, sig.y.gap = 1, y_lab=NULL, save = T, show = T) {
  
  data <- list('training' = training, 'validation' = validation)[[split]]
  
  result <- anova.plot(x = 'Subtype', y = y, data = data, colors = colors,
                       correction = 'fdr', sig.y.start = sig.y.start,
                       sig.y.gap = sig.y.gap, y_lab = y_lab,
                       font.size = 6, point.size = 2, point.linewidth = .5,
                       stat.textsize=3, stat.size=.4, mean.linewidth = .5)
  p <- result$plot
  
  if (show) {
    print(p)
  }
  
  if (save) {
    # save stuff
    stub <- sprintf('%s_%s', y, split)
    
    # save plot
    pname <- sprintf('%s_swarmplot.svg', stub)
    ggsave(file.path(odir, pname), plot = p, height = 2.5, width = 1.4, units = 'in')
    
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
result <- pipeline('training', 'CompositeMEM', sig.y.start = 2, sig.y.gap = 1, y_lab = 'Memory')
result <- pipeline('training', 'CompositeEXF', sig.y.start = 5, sig.y.gap = 1, y_lab = 'Executive Functioning')
result <- pipeline('training', 'CompositeLAN', sig.y.start = 5, sig.y.gap = 1, y_lab = 'Language')
result <- pipeline('training', 'CompositeVSP', sig.y.start = 3, sig.y.gap = 1, y_lab = 'Visuospatial')

# Validation
result <- pipeline('validation', 'Age', sig.y.start = 92, sig.y.gap = 2)
result <- pipeline('validation', 'Education', sig.y.start = 22, sig.y.gap = 2)
result <- pipeline('validation', 'SummarySUVRAmyloid', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Amyloid (SUVR)')
result <- pipeline('validation', 'SummarySUVRTau', sig.y.start = 2.5, sig.y.gap = .1, y_lab = 'Tau (SUVR)')
result <- pipeline('validation', 'TauLaterality', sig.y.start = 10, sig.y.gap = 1, y_lab = 'Tau Laterality')
result <- pipeline('validation', 'CDRSumBoxes', sig.y.start = 8, sig.y.gap = 1, y_lab = 'CDR (sum of boxes)')
result <- pipeline('validation', 'MMSETotal', sig.y.start = 31, sig.y.gap = 1.2, y_lab = 'MMSE')
result <- pipeline('validation', 'CompositeMEM', sig.y.start = 2, sig.y.gap = 1, y_lab = 'Memory')
result <- pipeline('validation', 'CompositeEXF', sig.y.start = 7, sig.y.gap = 1, y_lab = 'Executive Functioning')
result <- pipeline('validation', 'CompositeLAN', sig.y.start = 5, sig.y.gap = 1, y_lab = 'Language')
result <- pipeline('validation', 'CompositeVSP', sig.y.start = 3, sig.y.gap = 1, y_lab = 'Visuospatial')

# ===== Categorical Plots - Training =======

training$Sex <- ifelse(training$SexMale == 1, 'Male', 'Female')
stacked.barplot(training, 'TrainingMLSubtype', 'Sex', colors=c('#7b9acc', '#F2AA4C'),
                toptext.size=2) +
  xlab('Subtype') +
  theme(legend.position = 'top',
        text = element_text(size=6),
        legend.text = element_text(size=6),
        legend.key.size = unit(.1, 'in'),
        legend.margin = margin(b=-.2, unit='in')) +
  guides(fill = guide_legend(nrow=2, byrow=T))
ggsave(file.path(odir, 'sex_training_barplot.svg'), height = 2.5, width = 1.4, units = 'in')

training$E4 <- ifelse(training$HasE4 == 1, 'Carrier', 'Non-carrier')
training$E4 <- ifelse(is.na(training$HasE4), 'NA', training$E4)
training$E4 <- factor(training$E4, levels=c('Carrier', 'Non-carrier', 'NA'))
stacked.barplot(training, 'TrainingMLSubtype', 'E4',
                colors=c('#ed6f63', 'white', 'gray'),
                toptext.size=2) +
  xlab('Subtype') +
  theme(legend.position = 'top',
        text = element_text(size=6),
        legend.text = element_text(size=6),
        legend.key.size = unit(.1, 'in'),
        legend.margin = margin(b=-.2, unit='in')) +
  guides(fill = guide_legend(nrow=3, byrow=T))
ggsave(file.path(odir, 'hase4_training_barplot.svg'), height = 2.5, width = 1.4, units = 'in')

stacked.barplot(training, 'TrainingMLSubtype', 'AAStage',
                toptext.size=2,
                colors = c('#BFA9D1', '#C5EBCC', '#64A867', '#006400', 'gray')) +
  xlab("Subtype") + 
  theme(legend.position = 'none',
        text = element_text(size=6))
ggsave(file.path(odir, 'braak_training_barplot.svg'), height = 2.5, width = 1.4, units = 'in')

# ===== Categorical Plots - Validation =======

validation$Sex <- ifelse(validation$SexMale == 1, 'Male', 'Female')
stacked.barplot(validation, 'TrainingMLSubtype', 'Sex', colors=c('#7b9acc', '#F2AA4C'),
                toptext.size=2) +
  xlab('Subtype') +
  theme(legend.position = 'top',
        text = element_text(size=6),
        legend.text = element_text(size=6),
        legend.key.size = unit(.1, 'in'),
        legend.margin = margin(b=-.2, unit='in')) +
  guides(fill = guide_legend(nrow=2, byrow=T))
ggsave(file.path(odir, 'sex_validation_barplot.svg'), height = 2.5, width = 1.4, units = 'in')

validation$E4 <- ifelse(validation$HasE4 == 1, 'Carrier', 'Non-carrier')
validation$E4 <- ifelse(is.na(validation$HasE4), 'NA', validation$E4)
validation$E4 <- factor(validation$E4, levels=c('Carrier', 'Non-carrier', 'NA'))
stacked.barplot(validation, 'TrainingMLSubtype', 'E4',
                colors=c('#ed6f63', 'white', 'gray'),
                toptext.size=2) +
  xlab('Subtype') +
  theme(legend.position = 'top',
        text = element_text(size=6),
        legend.text = element_text(size=6),
        legend.key.size = unit(.1, 'in'),
        legend.margin = margin(b=-.2, unit='in')) +
  guides(fill = guide_legend(nrow=3, byrow=T))
ggsave(file.path(odir, 'hase4_validation_barplot.svg'), height = 2.5, width = 1.4, units = 'in')

stacked.barplot(validation, 'TrainingMLSubtype', 'AAStage',
                toptext.size=2,
                colors = c('#BFA9D1', '#C5EBCC', '#64A867', '#006400', 'gray')) +
  xlab("Subtype") + 
  theme(legend.position = 'none',
        text = element_text(size=6))
ggsave(file.path(odir, 'braak_validation_barplot.svg'), height = 2.5, width = 1.4, units = 'in')