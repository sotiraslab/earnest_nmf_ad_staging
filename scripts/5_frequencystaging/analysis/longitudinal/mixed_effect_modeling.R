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
df <- read.csv('/Users/earnestt1234/Desktop/atstaging/longitudinalTables/baseline.csv')
mmse.long <- read.csv('/Users/earnestt1234/Desktop/atstaging/longitudinalTables/mmse_long.csv')
cdr.long <- read.csv('/Users/earnestt1234/Desktop/atstaging/longitudinalTables/cdr_long.csv')

emm_options(pbkrtest.limit = 10000)

mixed.effect.modeling <- function(variable='mmse', split='training', autosave=T, root.output='/Users/earnestt1234/Desktop/atstaging') {
    
    # Select baseline data with stages assigned
    stages <- df %>%
        select(Subject, Stage, Age, SexMale, Split, ControlForStaging)

    # select data to use
    choices <- list('mmse'=mmse.long, 'cdr'=cdr.long)
    long.data <- choices[[variable]]
    if (is.null(long.data)) {
        stop('`variable` must be "cdr" or "mmse"')
    }
    MEASURE <- if (variable == 'mmse') 'MMSE' else 'CDRSumBoxes'
    SPLIT <- if (split == 'training') 'TrainingBaseline' else 'ValidationBaseline'
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
        filter(Split == SPLIT)

    # plot
    colors <- list(A0T0 = 'black',
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
    
    p <- ggplot(long.data, aes(x=YearsSinceBl, y=Score, color=Stage, fill=Stage)) +
        geom_smooth(alpha=.3, method='lm', linewidth=.5) +
        theme_bw() +
        theme(text = element_text(size=8, color='black'),
              axis.text.x = element_text(color='black'),
              axis.text.y = element_text(color='black'),
              legend.position = 'none') +
        ylab(YLAB) +
        xlab('Years') +
        scale_color_manual(values = colors) +
        scale_fill_manual(values = colors)

    print(p)

    # modeling
    fml <- as.formula(paste(MEASURE, ' ~ Stage * YearsSinceBl + Age + SexMale + (YearsSinceBl | Subject)', sep=''))
    model <- lmer(fml, data = long.data)

    # save output
    if (autosave) {
        odir <- file.path(root.output, 'plots', 'mixed_effect_modeling')
        dir.create(odir, showWarnings = F, recursive = T)

        bname <- sprintf('mem_split-%s_var-%s', split, variable)
        ggsave(filename = file.path(odir, str_c(bname, '.svg')), width=3.65, height=2, units='in')
        
        fe <- summary(model)$coefficients
        write.csv(fe, file.path(odir, str_c(bname, '_fixed_effects.csv')))

        em <- emmeans(model, 'Stage')
        em.summary <- summary(pairs(em, adjust='tukey')) %>%
            mutate(across(where(is.numeric), round, 3),
                     annotation = cut(p.value,
                                      breaks = c(0, 0.001, 0.01, 0.05, Inf),
                                      labels = c('***', "**", "*", ""),
                                      include.lowest = T),
                   p.value = ifelse(p.value == 0, '<0.001', p.value))
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
