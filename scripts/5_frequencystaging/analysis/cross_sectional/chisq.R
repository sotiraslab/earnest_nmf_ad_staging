
library(dplyr)
library(ggplot2)
library(stringr)
library(this.path)
library(tibble)
library(tidyr)

ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging'

path.master <- file.path(ROOT.OUTPUT, 'filesForR', 'maindata.csv')
df <- read.csv(path.master)

odir <- file.path(ROOT.OUTPUT, 'plots', 'chisq')
dir.create(odir, showWarnings = F)

# load the barplot script
path.barplot <- file.path(this.dir(), '..', '..','..', 'rsource', 'stacked_barplot.R')
source(path.barplot)

# === Stageable vs NS =======

train <- df %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False') %>%
  mutate(Stageable = ifelse(Stage == 'Atypical', 'NS', 'Stageable'))

sink(file.path(odir, 'training_ns_chiqs.txt'))

# Age
print('AGE')
x <- train[train$Stageable == 'Stageable', 'Age']
y <- train[train$Stageable != 'Stageable', 'Age']
t.test(x, y)

# Sex
print('SEX')
chisq.test(train$Stageable, train$SexMale)

# Race
print('RACE')
chisq.test(train$Stageable, train$Race)

# Dataset
print('DATASET')
chisq.test(train$Stageable, train$DataSet)
sink()

validation <- df %>%
  filter(Split == 'ValidationBaseline', ControlForStaging == 'False') %>%
  mutate(Stageable = ifelse(Stage == 'Atypical', 'NS', 'Stageable'))

sink(file.path(odir, 'validation_ns_chiqs.txt'))

# Age
print('AGE')
x <- validation[validation$Stageable == 'Stageable', 'Age']
y <- validation[validation$Stageable != 'Stageable', 'Age']
t.test(x, y)

# Sex
print('SEX')
chisq.test(validation$Stageable, validation$SexMale)

# Race
print('RACE')
chisq.test(validation$Stageable, validation$Race)

# Dataset
print('DATASET')
chisq.test(validation$Stageable, validation$DataSet)
sink()

# === CDR Distributuion =====

# This includes the NC individuals to match the 
# other plots modeling CDR-SB and MMSE

train <- df %>%
  filter(Split == 'TrainingBaseline', CDRBinned != '')

validation <- df %>%
  filter(Split == 'ValidationBaseline', CDRBinned != '')

cdrplot <- function(data) {
  plot.data <- data %>%
    group_by_at(c('CDRBinned', 'Stage')) %>%
    summarise(N=n()) %>%
    ungroup() %>%
    group_by(CDRBinned) %>%
    mutate(Percent = N / sum(N) * 100,
           CDRBinned = factor(CDRBinned, levels=c('1.0+', '0.5', '0.0')))
  
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
  
  p <- ggplot() +
    geom_col(
      data = plot.data,
      aes(fill=Stage, x=Percent, y=CDRBinned),
      color='black',
      position = 'stack',
      linewidth = 0.25) +
    xlab('Observations (%)') +
    ylab('CDR') +
    theme_classic() +
    scale_x_continuous(expand=expansion(add=0), breaks = c(0, 25, 50, 75, 100)) +
    theme(text = element_text(size=8),
          axis.line.x = element_blank(),
          legend.position = 'none',
          axis.line.x.bottom = element_line()) +
    scale_fill_manual(values = colors) 
  
  print(p)
  
  return (p)
}

plot <- cdrplot(train)
ggsave(file.path(odir, 'cdr_training.svg'), height = 1.6, width = 2.3, units = 'in')

plot <- cdrplot(validation)
ggsave(file.path(odir, 'cdr_validation.svg'), height = 1.6, width = 2.3, units = 'in')

# stats
chisq.test(train$Stage, train$CDRBinned)
