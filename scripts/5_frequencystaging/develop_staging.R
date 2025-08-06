# ---- imports ----
sh <- suppressPackageStartupMessages

sh(library(dplyr))
sh(library(gtools))
sh(library(mclust))
sh(library(scales))
sh(library(stringr))
sh(library(tidyr))

# ---- Paths -----
PATH.MASTER <- '/scratch/tom.earnest/atstaging//masterTables/_hardsave.csv'
PATH.WSCORES <- '/scratch/tom.earnest/atstaging//masterTables/FEATURE_WSCORES.csv'
PATH.HEATMAP.SCRIPT <- '/home/tom.earnest/code/at_nmf_sustain/scripts/rsource/stage_heatmaps.R'
PATH.STAGING.SCRIPT <- '/home/tom.earnest/code/at_nmf_sustain/scripts/rsource/assign_stages.R'
PATH.OUTPUT <- '/scratch/tom.earnest/atstaging/plots/stage_development'

dir.create(PATH.OUTPUT, showWarnings = F)

source(PATH.HEATMAP.SCRIPT)
source(PATH.STAGING.SCRIPT)

# ---- Parameters -----

# wscore cutoff threshold
thr <- 2.5

# ---- Helper functions -----
wscore.heatmap.routine <- function(df, plotpath=NULL) {
  wscore.cols <- colnames(df)[str_detect(colnames(df), 'WScore')]
  nice.names <- gsub('WScore', '', wscore.cols)
  wscores <- df[, wscore.cols]
  colnames(wscores) <- nice.names
  wmat <- ifelse(wscores > thr, 1, 0)
  wdf <- as.data.frame(wmat)
  colnames(wdf) <- nice.names
  
  recoding <- c('0.0' = 'SUVR+, CDR=0.0',
                '0.5' = 'SUVR+, CDR=0.5',
                '1.0+' = 'SUVR+, CDR>=1')
  df.plot <- cbind(df[, c('Subject', 'CDRBinned')], wdf) %>%
    mutate(CDRBinned = recode(na_if(CDRBinned, ''), !!!recoding, .missing='SUVR+, CDR=NA'))
  
  p <- stage.heatmap.by(df.plot, by='CDRBinned',
                   cols=nice.names,
                   cats=c('SUVR+, CDR=NA', unname(recoding)),
                   colors=c('#8a8a8a', '#440154FF', '#21908CFF', '#FDE725FF'),
                   empty.name = 'SUVR-') +
    theme(axis.text.x = element_text(size=10, angle=45, hjust=1, vjust = 1.15,
                                     margin = margin(t = -15, r = 0, b = 0, l = 100)),
          axis.text.y = element_blank(),
          plot.margin = margin(.1,1,.1,1, "cm"),
          plot.title = element_text(margin = margin(t = 0, r = 0, b = -20, l = 0)),
          legend.position = c(.95, .87),
          legend.justification = c("right", "top"),
          legend.box.just = "right",
          legend.margin = margin(6, 6, 6, 6),
          legend.title = element_blank())
  
  print(p)
  
  if (! is.null(plotpath)) {
    ggsave(plotpath, width = 6, height = 10, units = 'in')
  }
}

bootstrap.staging.routine <- function(df, plotpath=NULL) {
  wscore.cols <- colnames(df)[str_detect(colnames(df), 'WScore')]
  nice.names <- gsub('WScore', '', wscore.cols)
  wscores <- df[, wscore.cols]
  colnames(wscores) <- nice.names
  wmat <- ifelse(wscores > thr, 1, 0)
  wdf <- as.data.frame(wmat)
  colnames(wdf) <- nice.names
  
  sumPos <- colSums(wmat)
  stage.order <- sort(sumPos, decreasing = T)
  w.order <- names(stage.order)
  
  df.w <- as.data.frame(wmat)
  colnames(df.w) <- nice.names
  df.w <- df.w[, w.order]
  
  # === list all comparisons
  comparisons <- t(combn(w.order, 2))
  colnames(comparisons) <- c('A', 'B')
  n.compare <- nrow(comparisons)
  
  # === Calculate observed statistics
  
  observed.pos <- colSums(df.w)
  
  observed.diffs <- as.data.frame(comparisons)
  observed.diffs$Diff <- NA
  for (i in 1:nrow(observed.diffs)) {
    a <- observed.diffs[i, 'A']
    b <- observed.diffs[i, 'B']
    observed.diffs[i, 'Diff'] <- observed.pos[a] - observed.pos[b]
  }
  
  # === Bootstrapping =======
  
  set.seed(42)
  N <- 5000
  
  # Create holder for nulls for all comparisons
  nulls <- matrix(data = NA, nrow = n.compare, ncol = N)
  
  # run
  for (n in 1:N) {
    idx <- sample(1:nrow(df.w), size = nrow(df.w), replace = T)
    boot <- df.w[idx, ]
    boot.pos <- colSums(boot)
    null.pos <- boot.pos - observed.pos
    
    for (i in 1:nrow(comparisons)) {
      a <- comparisons[i, 'A']
      b <- comparisons[i, 'B']
      nulls[i, n] <- null.pos[a] - null.pos[b]
    }
  }
  
  # === P-values ========
  
  observed.diffs$p <- rowMeans(nulls >= observed.diffs$Diff)
  observed.diffs$p.corrected <- p.adjust(observed.diffs$p, method = 'fdr')
  observed.diffs$log.p.corrected <- -log10(observed.diffs$p.corrected)
  
  # === Collect all pairwise comparisons ========
  
  all.pairs <- as.data.frame(permutations(length(w.order), 2, w.order, repeats.allowed = T))
  colnames(all.pairs) <- c('A', 'B')
  
  all.pairs <- left_join(all.pairs, observed.diffs, by=c('A', 'B'))
  all.pairs$Main <- ! is.na(all.pairs$log.p.corrected)
  
  # ==== Plot  =========
  
  plot.data <- all.pairs %>%
    mutate(plot.p = ifelse(log.p.corrected >= 5, 5, log.p.corrected),
           plot.p = ifelse(plot.p<= -log10(0.05), 0, plot.p),
           plot.p = ifelse(is.na(plot.p), 0, plot.p),
           A = factor(A, levels=rev(colnames(df.w))),
           B = factor(B, levels=colnames(df.w)))
  
  p <- ggplot(data = plot.data, aes(x = B, y = A, fill = plot.p)) +
    geom_tile(linewidth=1, color='white') +
    coord_equal() +
    scale_fill_colormap(colormap='viridis') +
    scale_x_discrete(expand=c(0,0)) +
    scale_y_discrete(expand=c(0,0))+
    theme(panel.grid.major = element_blank(),
          panel.grid.minor = element_blank(),
          panel.background = element_rect(fill = "white"),
          axis.text.x = element_text(angle=30, hjust=1),
          text = element_text(size=15)) +
    labs(fill="-log10(p)")
  
  print(p)
  
  if (! is.null(plotpath)) {
    ggsave(plotpath, p, units='in', height = 8, width = 8)
  }
  
  # automatically infer stages
  # this shoudl be double checked against the graph/differences
  # but works with many cases I have seen
  first.rows <- observed.diffs %>% group_by(A) %>% filter(row_number()==1) %>% ungroup()
  regions.differ <- first.rows$p.corrected < 0.05
  
  stages <- rep(1, nrow(first.rows) + 1)
  stages[2:length(stages)] <- stages[2:length(stages)] + cumsum(regions.differ)
  names(stages) <- w.order
  
  # return stuff
  output <- list(
    data = observed.diffs,
    plot = p,
    stages = stages
  )
  
  return(output)
}

# ---- Load Data ----

# Load data
master <- read.csv(PATH.MASTER)
wscores <- read.csv(PATH.WSCORES)

master <- left_join(master, wscores, by=c('Subject', 'Session')) %>%
  drop_na(all_of(colnames(wscores)))

# separate into different groups
stage.data <- master %>%
  filter(str_detect(Split, 'Baseline'), ! ((CDRBinned == '0.0' | is.na(CDRBinned))  & FinalAmyloidStatus == 0 & GMMTauStatus == 0))
training <- stage.data[str_detect(stage.data$Split, 'Training'), ]
valA <- stage.data[stage.data$SameTracerValidationA == 'True', ]
valB <- stage.data[stage.data$SameTracerValidationB == 'True', ]
valC <- stage.data[stage.data$SameTracerValidationC == 'True', ]
valAll <- do.call(rbind, list(valA, valB, valC))

# ==== Bootstrap staging: training ====

wscore.heatmap.routine(training, plotpath = file.path(PATH.OUTPUT, 'training_wscore_positivity.svg'))
training.results <- bootstrap.staging.routine(training, plotpath = file.path(PATH.OUTPUT, 'training_bootstrap_staging.svg'))

# ==== Bootstrap staging: Validation A ====

wscore.heatmap.routine(valA, file.path(PATH.OUTPUT, 'validationA_wscore_positivity.svg'))
valA.results <- bootstrap.staging.routine(valA, file.path(PATH.OUTPUT, 'validationA_bootstrap_staging.svg'))

# ==== Bootstrap staging: Validation B ====

wscore.heatmap.routine(valB, file.path(PATH.OUTPUT, 'validationB_wscore_positivity.svg'))
valB.results <- bootstrap.staging.routine(valB, file.path(PATH.OUTPUT, 'validationB_bootstrap_staging.svg'))

# ==== Bootstrap staging: Validation C ====

wscore.heatmap.routine(valC, file.path(PATH.OUTPUT, 'validationC_wscore_positivity.svg'))
valC.results <- bootstrap.staging.routine(valC, file.path(PATH.OUTPUT, 'validationC_bootstrap_staging.svg'))

# ==== Bootstrap staging: Validation All ====

wscore.heatmap.routine(valAll, file.path(PATH.OUTPUT, 'validationAll_wscore_positivity.svg'))
valAll.results <- bootstrap.staging.routine(valAll, file.path(PATH.OUTPUT, 'validationAll_bootstrap_staging.svg'))

# ==== Regional order by dataset =======

# plot of order

positivity.order <- function(results, name) {
  stages <- results$stages
  frame <- data.frame(Region=names(stages), Order=1:length(stages))
  colnames(frame) <- c('Region', name)
  return(frame)
}

training.order <- positivity.order(training.results, 'Training')
valA.order <- positivity.order(valA.results, 'ValidationA')
valB.order <- positivity.order(valB.results, 'ValidationB')
valC.order <- positivity.order(valC.results, 'ValidationC')
valAll.order <- positivity.order(valAll.results, 'ValidationCombined')

data <- training.order %>%
  left_join(valA.order, by='Region') %>%
  left_join(valB.order, by='Region') %>%
  left_join(valC.order, by='Region') %>%
  left_join(valAll.order, by='Region')

plot.data <- data %>%
  pivot_longer(-Region, names_to = 'Split', values_to = 'Order') %>%
  mutate(
    Split = factor(Split, levels = c('Training', 'ValidationA', 'ValidationB', 'ValidationC', 'ValidationCombined')),
    Region = factor(Region, levels = rev(names(training.results$stages))),
    Order = factor(Order)
  )

ggplot(plot.data, aes(x=Split, y=Region, fill=Order, label=Order)) +
  geom_tile() +
  geom_text() +
  coord_equal() +
  scale_fill_colormap(colormap='jet', discrete = T, reverse = T) +
  scale_x_discrete(expand=c(0,0)) +
  scale_y_discrete(expand=c(0,0)) +
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank(),
        panel.background = element_rect(fill = "#440154ff"),
        axis.text.x = element_text(angle=30, hjust=1),
        text = element_text(size=15))

ggsave(file.path(PATH.OUTPUT, 'compare_regional_order.svg'),
       width = 6, height = 10, units = 'in')

# Friedman test for this analysis
sink(file.path(PATH.OUTPUT, 'compare_regional_order_friedman.txt'))
friedman.test(as.matrix(data))
sink()

# inversion tests?
inversions <- function(x) {
  ans <- 0
  
  # Iterate through the vector
  for (i in 1:(length(x) - 1)) {
    for (j in (i + 1):length(x)) {
      if (x[i] > x[j]) {
        ans <- ans + 1
      }
    }
  }
  return (ans)
}

repeats <- 5000
null.dist <- rep(NA, repeats)
set.seed(42)

for (i in 1:repeats) {
  x <- sample(1:11, size=11, replace = F)
  null.dist[i] <- inversions(x)
}

sink(file.path(PATH.OUTPUT, 'compare_regional_order_inversions.txt'))
cat('\nValidation A p-value: ', mean(null.dist <= inversions(data$ValidationA)))
cat('\nValidation B p-value: ', mean(null.dist <= inversions(data$ValidationB)))
cat('\nValidation C p-value: ', mean(null.dist <= inversions(data$ValidationC)))
cat('\nValidation Combined p-value: ', mean(null.dist <= inversions(data$ValidationCombined)))
sink()

# ==== Positivity rate by dataset =====

# Plot of positivity rate

positivity.rate <- function(df, fieldname, thr=2.5) {
  wscore.cols <- colnames(df)[str_detect(colnames(df), 'WScore')]
  nice.names <- gsub('WScore', '', wscore.cols)
  wscores <- df[, wscore.cols]
  colnames(wscores) <- nice.names
  wmat <- ifelse(wscores > thr, 1, 0)
  wdf <- as.data.frame(wmat)
  
  rates <- sort(colMeans(wdf), decreasing=T)
  frame <- data.frame(Region=names(rates), PositivityRate=unname(rates))
  colnames(frame) <- c('Region', fieldname)
  return (frame)
}

training.pos <- positivity.rate(training, 'Training')
valA.pos <- positivity.rate(valA, 'ValidationA')
valB.pos <- positivity.rate(valB, 'ValidationB')
valC.pos <- positivity.rate(valC, 'ValidationC')
valAll.pos <- positivity.rate(valAll, 'ValidationCombined')

data <- training.pos %>%
  left_join(valA.pos, by='Region') %>%
  left_join(valB.pos, by='Region') %>%
  left_join(valC.pos, by='Region') %>%
  left_join(valAll.pos, by='Region')

plot.data <- data %>%
  pivot_longer(-Region, names_to = 'Split', values_to = 'Positivity') %>%
  mutate(
    Split = factor(Split, levels = c('Training', 'ValidationA', 'ValidationB', 'ValidationC', 'ValidationCombined')),
    Region = factor(Region, levels = rev(names(training.results$stages)))
  )

ggplot(plot.data, aes(x=Split, y=Region, fill=Positivity)) +
  geom_tile() +
  coord_equal() +
  scale_fill_colormap(colormap='cubehelix') +
  scale_x_discrete(expand=c(0,0)) +
  scale_y_discrete(expand=c(0,0)) +
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank(),
        panel.background = element_rect(fill = "#440154ff"),
        axis.text.x = element_text(angle=30, hjust=1),
        text = element_text(size=15))

ggsave(file.path(PATH.OUTPUT, 'compare_regional_positivity.svg'),
       width = 6, height = 10, units = 'in')

# ==== Stage assignment by dataset =====

# plot of stages

positivity.stages <- function(results, name) {
  stages <- results$stages
  frame <- data.frame(Region=names(stages), Stage=unname(stages))
  colnames(frame) <- c('Region', name)
  return(frame)
}

training.stages <- positivity.stages(training.results, 'Training')
valA.stages <- positivity.stages(valA.results, 'ValidationA')
valB.stages <- positivity.stages(valB.results, 'ValidationB')
valC.stages <- positivity.stages(valC.results, 'ValidationC')
valAll.stages <- positivity.stages(valAll.results, 'ValidationCombined')

data <- training.stages %>%
  left_join(valA.stages, by='Region') %>%
  left_join(valB.stages, by='Region') %>%
  left_join(valC.stages, by='Region') %>%
  left_join(valAll.stages, by='Region')

plot.data <- data %>%
  pivot_longer(-Region, names_to = 'Split', values_to = 'Stage') %>%
  mutate(
    Split = factor(Split, levels = c('Training', 'ValidationA', 'ValidationB', 'ValidationC', 'ValidationCombined')),
    Region = factor(Region, levels = rev(names(training.results$stages))),
    Stage = factor(Stage)
  )

ggplot(plot.data, aes(x=Split, y=Region, fill=Stage, label=Stage)) +
  geom_tile() +
  geom_text() +
  coord_equal() +
  scale_fill_colormap(colormap='viridis', discrete = T, reverse = T) +
  scale_x_discrete(expand=c(0,0)) +
  scale_y_discrete(expand=c(0,0)) +
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank(),
        panel.background = element_rect(fill = "#440154ff"),
        axis.text.x = element_text(angle=30, hjust=1),
        text = element_text(size=15))

ggsave(file.path(PATH.OUTPUT, 'compare_stage_assignment.svg'),
       width = 6, height = 10, units = 'in')

# ==== Assign stages ======

check.stages <- function(stages) {
  stages <- unname(stages)
  a <- stages[1] == 1
  b <- all(diff(stages) %in% c(0, 1))
  
  if (! (a & b)) {
    stop("Stages either do not start at 1 or do not contain contiguous integers.")
  }
  
  return (TRUE)
}

atstaging <- function(data, staging.results, thr = 2.5) {
  # extract the actual stages
  stages <- staging.results$stages
  
  # "WScore" suffix is dropped from staging results, so added back here
  names(stages) <- str_c(names(stages), "WScore")
  
  # pull out amyloid & tau regions
  amy.regions <- names(stages)[str_detect(names(stages), 'PAC.*WScore')]
  tau.regions <- names(stages)[str_detect(names(stages), 'PTC.*WScore')]
  all.regions <- c(amy.regions, tau.regions)
  
  # get stage indices for amyloid and tau
  # add correction for indices potentially not starting at 1
  amy.stages <- stages[amy.regions]
  tau.stages <- stages[tau.regions]
  
  amy.stages = amy.stages - min(amy.stages) + 1
  tau.stages = tau.stages - min(tau.stages) + 1
  
  # Check to make sure stages look good
  ans <- check.stages(amy.stages)
  ans <- check.stages(tau.stages)
  
  # convert data to binary positivity
  bin.data <- as.data.frame(ifelse(data[, all.regions] > thr, 1, 0))
  
  # get the stages
  full.stage <- assign.stages(data = bin.data, regions = all.regions, stage.grouping = unname(stages), p = 'any', atypical = 'NS')
  a.stage <- assign.stages(data = bin.data, regions = amy.regions, stage.grouping = unname(amy.stages), p = 'any', atypical = 'NS')
  t.stage <- assign.stages(data = bin.data, regions = tau.regions, stage.grouping = unname(tau.stages), p = 'any', atypical = 'NS')
  
  result <- data.frame(StageNumeric = full.stage, StageAmyloid = a.stage, StageTau = t.stage) %>%
    mutate(
      Stage = recode(StageNumeric, '0'='A0T0', '1'='A1T0', '2'='A2T0', '3'='A2T1',
                          '4'='A2T2', '5'='A2T3', '6'='A2T4', 'NS'='Atypical'),
      StageDual = str_c('A', StageAmyloid, 'T', StageTau),
      StageDual = ifelse(StageAmyloid == '0' & StageTau != '0', 'A-T+', StageDual),
      StageLabelNS = ifelse(Stage == 'Atypical', 'Other', Stage),
      StageLabelNS = ifelse(StageAmyloid == '0' & StageTau != '0', 'A0T+', StageLabelNS),
      StageLabelNS = ifelse(StageAmyloid == '1' & StageTau %in% c('1', '2', '3', '4'), 'A1T+', StageLabelNS),
      StageLabelNS = ifelse((StageAmyloid != 'NS') & (StageTau == 'NS') & (data$PTCMedialTemporalWScore < 2.5), 'MTL-', StageLabelNS))
  return (result)
}

df.staging <- atstaging(master, training.results)
valA.staging <- atstaging(master, valA.results)
valB.staging <- atstaging(master, valB.results)
valC.staging <- atstaging(master, valC.results)
valAll.staging <- atstaging(master, valAll.results)

df.staging$StageValA <- valA.staging$StageNumeric
df.staging$StageValB <- valB.staging$StageNumeric
df.staging$StageValC <- valC.staging$StageNumeric
df.staging$StageValAll <- valAll.staging$StageNumeric

# ==== ARI Analysis =====

# ARI analysis
cols <- c('StageNumeric', 'StageValA', 'StageValB', 'StageValC', 'StageValAll')
matdim <- length(cols)
ARIs <- matrix(data=NA, nrow=matdim, ncol=matdim)

join <- cbind(master, df.staging)
join <- join %>%
  filter(! ((CDRBinned == '0.0' | is.na(CDRBinned))  & FinalAmyloidStatus == 0 & GMMTauStatus == 0))

for (i in 1:matdim) {
  for (j in 1:matdim) {
    cola <- cols[i]
    colb <- cols[j]
    a <- join[[cola]]
    a <- as.numeric(ifelse(a == 'NS', 999, a))
    b <- join[[colb]]
    b <- as.numeric(ifelse(b == 'NS', 999, b))
    ARIs[i, j] <- adjustedRandIndex(a, b)
  }
}

plot.data <- as.data.frame(ARIs)
colnames(plot.data) <- cols
plot.data$SystemA <- cols
plot.data <- plot.data %>%
  pivot_longer(-SystemA, names_to = 'SystemB', values_to = 'ARI') %>%
  mutate(SystemA = factor(SystemA, levels=rev(cols)),
         SystemB = factor(SystemB, levels=cols),
         ARIround = round(ARI, 2),
         ARIminmax = (ARI - min(ARI)) / (max(ARI) - min(ARI)),
         TextColor = ifelse(ARIminmax < 0.4, 'white', 'black'))

ggplot(plot.data) +
  geom_tile(aes(x=SystemB, y=SystemA, fill=ARI)) +
  scale_fill_colormap(colormap='viridis') +
  coord_equal() +
  geom_text(aes(x=SystemB, y=SystemA, label=ARIround, color=TextColor)) +
  scale_color_identity() +
  scale_x_discrete(expand=c(0,0)) +
  scale_y_discrete(expand=c(0,0)) +
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank(),
        panel.background = element_rect(fill = "#440154ff"),
        axis.text.x = element_text(angle=30, hjust=1),
        text = element_text(size=15))

ggsave(file.path(PATH.OUTPUT, 'ari_staging_analysis.svg'),
       width = 8, height = 8, units = 'in')

# ==== SAVE ====

master.folder <- dirname(PATH.MASTER)

# filter indicating subjects that are included in staging analysis
filter.staging <- master[, c('Subject', 'Session')]
filter.staging$Keep <- TRUE
write.csv(filter.staging, file.path(master.folder, 'FILTER_STAGING.csv'), quote = F, na = '', row.names = F)

# feature containing the staging analyses
feature.staging <- cbind(master[, c('Subject', 'Session')], df.staging)
feature.staging$ControlForStaging <- (
  str_detect(master$Split, 'Baseline') &
  ((master$CDRBinned == '0.0' | is.na(master$CDRBinned)) & master$FinalAmyloidStatus == 0 & master$GMMTauStatus == 0)
)
write.csv(feature.staging, file.path(master.folder, 'FEATURE_STAGING.csv'), quote = F, na = '', row.names = F)