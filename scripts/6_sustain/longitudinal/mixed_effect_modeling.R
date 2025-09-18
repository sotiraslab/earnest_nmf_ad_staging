# imports
library(dplyr)
library(emmeans)
library(gtools)
library(ggplot2)
library(lme4)
library(lmerTest)
library(lubridate)
library(scales)
library(stringr)
library(tidyr)

# Load the data, which is split out by collect_longitudinal_assessments.py
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

df <- read.csv(file.path(ROOT.OUTPUT, 'longitudinalTables', 'baseline.csv'))
mmse.long <- read.csv(file.path(ROOT.OUTPUT, 'longitudinalTables', 'mmse_long.csv'))
cdr.long <- read.csv(file.path(ROOT.OUTPUT, 'longitudinalTables', 'cdr_long.csv'))

# load subtypes
master <- read.csv(file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv'))
merger <- master %>% 
  mutate(Subtype = ifelse(ControlForStaging == 'True', 'Control', TrainingMLSubtype)) %>%
  select(Subject, Session, Subtype)
df <- left_join(df, merger, by = c('Subject', 'Session'))

# get inclusion subjects
training.ads <- master %>%
  filter(
    Split == 'TrainingBaseline',
    ControlForStaging == "False",
    TrainingMLStage != 0,
    TrainingSubtypeValid ==1 
  ) %>%
  pull(Subject)

validation.ads <- master %>%
  filter(
    Split == 'ValidationBaseline',
    ControlForStaging == "False",
    TrainingMLStage != 0,
    TrainingSubtypeValid ==1 
  ) %>%
  pull(Subject)

training.nc <- master %>%
  filter(
    Split == 'TrainingBaseline',
    ControlForStaging == "True"
  ) %>%
  pull(Subject)

validation.nc <- master %>%
  filter(
    Split == 'ValidationBaseline',
    ControlForStaging == "True"
  ) %>%
  pull(Subject)

mixed.effect.modeling <- function(variable='mmse', split='training', autosave=T) {
    
    # Select baseline data with stages assigned
    stages <- df %>%
        select(Subject, Subtype, Age, SexMale, Split, ControlForStaging)

    # select data to use
    choices <- list('mmse'=mmse.long, 'cdr'=cdr.long)
    long.data <- choices[[variable]]
    if (is.null(long.data)) {
        stop('`variable` must be "cdr" or "mmse"')
    }
    MEASURE <- if (variable == 'mmse') 'MMSE' else 'CDRSumBoxes'
    SUBS <- if (split == 'training') c(training.ads, training.nc) else c(validation.ads, validation.nc)
    YLAB <- if (variable == 'mmse') 'MMSE' else 'CDR (sum of boxes)'

    # create longitudinal df for MEM
    long.data <- long.data %>%
        group_by(Subject) %>% 
        mutate(DateLongitudinal = as_datetime(ymd(DateLongitudinal))) %>%
        arrange(Subject, DateLongitudinal) %>%
        mutate(
            YearsSinceBl = as.numeric(difftime(DateLongitudinal, first(DateLongitudinal), units='days')) / 365.25,
            Score = get(!!MEASURE),
            BaselineScore = first(Score)
        ) %>%
        filter(n() >= 2) %>% 
        ungroup() %>%
        drop_na(Score) %>%
        left_join(stages, by = 'Subject') %>%
        filter(Subject %in% SUBS)

    # plot
    colors <- c(
      'Control' = 'gray',
      'S1' = '#db2b39',
      'S2' = '#053c5e',
      'S3' = '#f3a712' 
    )
    
    p <- ggplot(long.data, aes(x=YearsSinceBl, y=Score, color=Subtype, fill=Subtype)) +
        geom_smooth(alpha=.3, method='lm') +
        theme_bw() +
        theme(text = element_text(size=15)) +
        ylab(YLAB) +
        xlab('Years') +
        scale_color_manual(values = colors) +
        scale_fill_manual(values = colors)

    print(p)

    # modeling
    fml <- as.formula(paste(MEASURE, ' ~ Subtype * YearsSinceBl + Age + SexMale + (YearsSinceBl | Subject)', sep=''))
    model <- lmer(fml, data = long.data)

    # save output
    if (autosave) {
        odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'mixed_effect_modeling')
        dir.create(odir, showWarnings = F, recursive = T)

        bname <- sprintf('mem_split-%s_var-%s', split, variable)
        ggsave(filename = file.path(odir, str_c(bname, '.svg')), width=8, height=6, units='in')
        
        fe <- summary(model)$coefficients
        write.csv(fe, file.path(odir, str_c(bname, '_fixed_effects.csv')))

        em <- emmeans(model, 'Subtype')
        em.summary <- summary(pairs(em, adjust='tukey')) %>%
            mutate(across(where(is.numeric), round, 3),
                     annotation = cut(p.value,
                                      breaks = c(0, 0.001, 0.01, 0.05, Inf),
                                      labels = c('***', "**", "*", ""),
                                      include.lowest = T))
        write.csv(em.summary, file.path(odir, str_c(bname, '_emmeans.csv')))
    }

    # return
    output <- list(plot = p, model = model)
    return (output)
}

output <- mixed.effect.modeling(variable='mmse', split='training', autosave=T)
output <- mixed.effect.modeling(variable='cdr', split='training', autosave=T)
output <- mixed.effect.modeling(variable='mmse', split='validation', autosave=T)
output <- mixed.effect.modeling(variable='cdr', split='validation', autosave=T)
