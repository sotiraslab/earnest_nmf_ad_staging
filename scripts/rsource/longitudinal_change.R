
library(dplyr)
library(ggplot2)
library(lme4)
library(tidyr)

calc.longitudinal.change <- function(baseline, longitudinal,
                                     variable, date.column,
                                     id.column='RID', age.column='Age',
                                     plot = TRUE, plot.by='CDRBinned') {

  joiner <- longitudinal %>%
    select(!!id.column, !!date.column, !!variable, !!plot.by) %>%
    rename(ID=!!id.column, DATE=!!date.column, VAR=!!variable)
  
  long.data <- baseline %>%
    select(!!id.column, !!date.column, !!age.column, !!plot.by) %>%
    rename(ID=!!id.column, DATE.BL=!!date.column, AGE=!!age.column, PLOTBY=!!plot.by) %>%
    left_join(joiner, by='ID') %>%
    group_by(ID) %>%
    mutate(DELTA = as.numeric(difftime(DATE, DATE.BL, units='days')) / 365.25,
           LONG.AGE = AGE + DELTA) %>%
    filter(DATE >= DATE.BL) %>%
    filter(n() >= 2) %>%
    drop_na(VAR) %>%
    ungroup()
  
  # longitudinal modelling
  m <- lmer(VAR ~ DELTA + (1+DELTA|ID), data=long.data)
  long.data$VAR.PREDICT <- predict(m, long.data)
  
  if (plot) {
    p <- ggplot(long.data, aes(x=LONG.AGE, y=VAR)) +
    geom_point(aes(color=PLOTBY), alpha = .7) +
    geom_line(aes(y=VAR.PREDICT, group=ID, color=PLOTBY), alpha= .7) +
    ggtitle(variable)
  
  print(p)
  }
  
  final.name <- paste('Delta', variable, sep='')
  
  coefs <- coef(m)$ID %>%
    select(DELTA) %>%
    rownames_to_column(var='ID') %>%
    mutate(ID = as.character(ID))
  colnames(coefs) <- c(id.column, final.name)
  
  result <- left_join(baseline, coefs, by=id.column)
  
  return (result)
}
