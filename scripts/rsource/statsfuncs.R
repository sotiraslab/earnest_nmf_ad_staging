library(car)
library(dplyr)
library(multcomp)
library(stringr)
library(tidyr)

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