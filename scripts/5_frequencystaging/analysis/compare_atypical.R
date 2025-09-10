library(car)
library(dplyr)
library(lubridate)
library(multcomp)
library(stringr)
library(tidyr)


# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

# functions
residualize.loadings <- function(data) {
  cols <- colnames(data)
  pacs <- cols[str_detect(cols, 'PAC.*SUVR')]
  ptcs <- cols[str_detect(cols, 'PTC.*SUVR')]
  
  for (pac in pacs) {
    dest <- sprintf('%sResidualized', pac)
    fml <- as.formula(sprintf('%s ~ SummarySUVRAmyloid', pac))
    m <- lm(fml, data = data)
    data[[dest]] <- m$residuals
  }
  
  for (ptc in ptcs) {
    dest <- sprintf('%sResidualized', ptc)
    fml <- as.formula(sprintf('%s ~ SummarySUVRTau', ptc))
    m <- lm(fml, data = data)
    data[[dest]] <- m$residuals
  }
  
  return (data)
}

run.ancova <- function(dependent, independent, covariates, data) {
  covariates <- covariates[! covariates == dependent]
  
  fml <- as.formula(paste(dependent, '~', independent, '+', paste(covariates, collapse = ' + ')))
  fac.levels <- levels(data[[independent]])
  n.levels <- length(fac.levels)
  n.comparisons <- choose(n.levels, 2)
  
  # https://www.r-bloggers.com/2021/07/how-to-perform-ancova-in-r/
  ancova_model <- lm(fml, data = data)
  main <- Anova(ancova_model, type='III')
  mcp_args <- setNames(list("Tukey"), independent)
  postHocs <- glht(ancova_model, linfct = do.call(mcp, mcp_args))
  summary.postHocs <- summary(postHocs)
  
  # get means for each level of independent
  means <- rep(NA, n.levels)
  for (i in 1:n.levels) {
    level <- fac.levels[i]
    means[i] <- as.character(round (mean(data[data[[independent]] == level, dependent], na.rm = T), 3))
  }
  names(means) <- fac.levels
  means <- as.list(means)
  
  # get overall p
  f_stat <- summary(ancova_model)$fstatistic
  overall_f <- f_stat[1]
  overall_p <- pf(f_stat[1], f_stat[2], f_stat[3], lower.tail = FALSE)
  
  # get post hoc comparison results
  # NOTE: Later, will need to not count signitifant tests where the overall
  # model is not significant
  post.p <- summary.postHocs$test$pvalues
  names(post.p) <- str_replace(names(summary.postHocs$test$coefficients), ' - ', ' vs. ')
  post.p <- as.list(post.p)
  
  # construct output
  output <- c(
    list(Variable = dependent), means, list(p=overall_p), post.p
  )
  
  return (output)
}

run.chisq.binary.dependent <- function(dependent, independent, data) {

  fac.levels <- levels(data[[independent]])
  n.levels <- length(fac.levels)
  n.comparisons <- choose(n.levels, 2)
  
  main.test <- chisq.test(data[[independent]], data[[dependent]])
  
  # get frequencies for each level of independent
  freqs <- rep(NA, n.levels)
  for (i in 1:n.levels) {
    level <- fac.levels[i]
    level.size <- sum(data[[independent]] == level)
    level.freq <- sum((data[[independent]] == level) & (data[[dependent]] == 1), na.rm = T)
    pct <- round(level.freq / level.size * 100, 1)
    freqs[i] <- sprintf('%s (%s/%s)', pct, level.freq, level.size)
  }
  names(freqs) <- fac.levels
  freqs <- as.list(freqs)
  
  # get overall p
  overall_p <- main.test$p.value
  
  # get post-hoc comparisons
  pairs <- combn(fac.levels, 2)
  post.p <- rep(NA, n.comparisons)
  for (i in 1:n.levels) {
    a <- pairs[1, i]
    b <- pairs[2, i]
    sub <- data[data[[independent]] %in% c(a, b), ]
    test <- chisq.test(sub[[independent]], sub[[dependent]])
    post.p[i] <- test$p.value
    names(post.p)[i] <- sprintf('%s vs. %s', b, a)
  }
  post.p <- as.list(post.p)
  
  output <- c(
    list(Variable = dependent), freqs, list(p=overall_p), post.p
  )
}

pipeline <- function(data) {
    dependents <- c(
      'Age', 'SexMale', 'Education', 'BMI', "HasE4", 'MMSETotal', 'CDRSumBoxes',
      colnames(data)[str_detect(colnames(data), 'Residualized')]
    )
    binary.dependents <- c('SexMale', 'HasE4')
    
    result.rows <- vector(mode = 'list', length = length(dependents))
    
    for (i in 1:length(dependents)) {
      dependent <- dependents[i]
      
      if (dependent %in% binary.dependents) {
        result.rows[[i]] <- run.chisq.binary.dependent(
          dependent = dependent,
          independent = 'StageType',
          data = data
        )
      } else {
        result.rows[[i]] <- run.ancova(
          dependent = dependent,
          independent = 'StageType',
          covariates = c('Age', 'SexMale'),
          data = data
          )
      }
    }
    
    result <- bind_rows(result.rows)
    pairwise.column <- str_detect(colnames(result), ' vs. ') # this could be improved but so be it
    missing.atypical <- ! str_detect(colnames(result), 'Atypical')
    result <- result[, ! (pairwise.column & missing.atypical)]
    
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
             p = round(p, 3)
      ) %>%
      pivot_wider(id_cols = all_of(id.cols), names_from = Comparison, values_from = annot)
    
    return (result.star)
}

# RUN

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

training <- residualize.loadings(training)
validation <- residualize.loadings(validation)
train.result <- pipeline(training)
validaiton.result <- pipeline(validation)

# Save
odir <- file.path(ROOT.OUTPUT, 'tables')
dir.create(odir, showWarnings = F)
write.csv(train.result, file.path(odir, 'training_atypical_modeling.csv'), row.names = F)
write.csv(validaiton.result, file.path(odir, 'validation_atypical_modeling.csv'), row.names = F)
