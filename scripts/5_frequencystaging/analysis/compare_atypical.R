library(car)
library(dplyr)
library(lubridate)
library(multcomp)
library(stringr)


# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

# Load main data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_covariates.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA) %>%
  filter(Stage != 'A0T0') %>%
  mutate(StageType = ifelse(Stage == 'Atypical', 'Atypical', 'Typical'),
         StageType = ifelse(StageType == 'Typical' & Stage %in% c('A1T0', 'A2T0'), 'A1T0-A2T0', StageType),
         StageType = ifelse(StageType == 'Typical' & Stage %in% c('A2T1', 'A2T2', 'A2T3', 'A2T4'), 'A2T1-A2T4', StageType),
         StageType = factor(StageType, levels=c('Atypical', 'A1T0-A2T0', 'A2T1-A2T4'))
         )
training <- master %>%
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False')
validation <- master %>%
  filter(Split == 'ValidationBaseline', ControlForStaging == 'False')

run.ancovas <- function(data) {
  
  # establish dependent variables to test
  dependents <- c(
    'Age', 'Education', 'BMI', 'MMSETotal', 'CDRSumBoxes',
    "PACParietalSUVR", "PACFrontalSUVR", "PACOccipitalSUVR", "PACSensorimotorSUVR",
    "PTCMedialTemporalSUVR", "PTCLeftParietalTemporalSUVR", "PTCRightParietalTemporalSUVR", "PTCOccipitalSUVR",
    "PTCFrontalSUVR", "PTCSensorimotorSUVR",  "PTCInsularMedialFrontalSUVR"
  )
  n.dependents <- length(dependents)
  
  # construct output
  mat <- matrix(data=NA, nrow = n.dependents, ncol = 6)
  output <- as.data.frame(mat)
  colnames(output) <- c('Variable', 'Atypical', 'A1T0-A2T0', 'A2T1-A2T4', 'F', 'p')
  
  # fit models
  for (i in 1:n.dependents) {
    dependent <- dependents[i]
    fml <- as.formula(sprintf('%s ~ StageType + SummarySUVRAmyloid + SummarySUVRTau', dependent))
    
    output[i, 'Variable'] <- dependent
    output[i, 'Atypical'] <- round(mean(data[data$StageType == 'Atypical', dependent], na.rm = T), 2)
    output[i, 'A1T0-A2T0'] <- round(mean(data[data$StageType == 'A1T0-A2T0', dependent], na.rm = T), 2)
    output[i, 'A2T1-A2T4'] <- round(mean(data[data$StageType == 'A2T1-A2T4', dependent], na.rm = T), 2)
    
    # https://www.r-bloggers.com/2021/07/how-to-perform-ancova-in-r/
    ancova_model <- lm(fml, data = data)
    main <- Anova(ancova_model, type='III')
    postHocs <- glht(ancova_model, linfct = mcp(StageType = "Tukey"))
    summary.postHocs <- summary(postHocs)
    
    # F-value for overall model
    f_stat <- summary(ancova_model)$fstatistic
    overall_f <- f_stat[1]
    overall_p <- pf(f_stat[1], f_stat[2], f_stat[3], lower.tail = FALSE)
    output[i, 'F'] <- round(overall_f, 2)
    output[i, 'p'] <- overall_p
    
    # add stars to posthoc comparisons
    pvalues <- summary.postHocs$test$pvalues
    stars <- cut(pvalues, breaks = c(0, 0.001, 0.01, 0.05, Inf), labels = c('***', "**", "*", ""), include.lowest = T)
    
    output[i, 'A1T0-A2T0'] <- str_c(output[i, 'A1T0-A2T0'], stars[1])
    output[i, 'A2T1-A2T4'] <- str_c(output[i, 'A2T1-A2T4'], stars[2])
  }
  output$p <- ifelse(output$p < 0.001, '<0.001', round(output$p, 3))
  return (output)
}

output <- run.ancovas(training)
path.output <- file.path(ROOT.OUTPUT, 'tables', 'statistical_comparison_of_atypical.csv')
write.csv(output, path.output)