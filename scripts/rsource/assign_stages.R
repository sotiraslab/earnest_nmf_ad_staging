assign.stages <- function(data, regions, stage.grouping, p='any', atypical=NA) {
  
  # Overview
  # --------
  #
  # Function for converting binary assessments of pathology into stage
  # assignments.  Applies typical staging logic of finding the highest stage
  # such that a subject is positive for pathology in that stage and all
  # preceding ones.  Uses a different labeling for people who meet criteria
  # for a higher stage but not all preceding ones.
  
  # For PTC staging specifcally, this function is not needed.
  # See `ptc.staging()`, below, which calls this.
  
  # Parameters
  # ----------
  # data (data.frame) : Dataset (subjects x features)
  # regions (character) : Columns to stage on.  Each entry should
  #     correspond to the name of a binary column in `data`.
  # stage.grouping (integer) : A vector of integers used to group regions
  #     into stages. This should be the same length as `regions` and contain
  #     a non-decreasing collection of integers starting from 1
  #     E.g., `c(1, 1, 2, 3)` groups the first two regions into one stage,
  #     and puts the 3rd and 4th into individual stages.
  # p (float in [0, 1], 'any', or 'all') : Sets how many sub-regions a person
  #     has to have pathology in to meet criteria for a stage.  If "all",
  #     they must be positive in all regions of the stage.  If "any", they
  #     must be positive in 1 region for the stage.  Otherwise, can be 
  #     a float between 0 and 1 to signify the proportion of regions the
  #     person should be positive for.  E.g., use `0.5` to indicate that
  #     the person must show positivity in more than half of the regions
  #     corresponding to a given stage.  This is more useful when 
  #     having stages that include many sub-regions.
  # atypical (numeric or character) : Symbol to use for people who are
  #     atypical/non-stageable.
  
  staged.data <- data.frame(id=1:nrow(data))
  unique.stages <- unique(stage.grouping)
  n <- length(unique.stages)
  for (i in sort(unique.stages)) {
    regions.current <- as.character(regions[stage.grouping == i])
    sub.data <- data[, regions.current, drop=F]
    ps <- rowSums(sub.data) / length(regions.current)
    if (p == 'any') {
      positive.for.stage <- as.numeric(ps > 0)
    } else if (p == 'all') {
      positive.for.stage <- as.numeric(ps == 1)
    } else {
      positive.for.stage <- as.numeric(ps >= p)
    }
    staged.data[[sprintf('positive.%s', i)]] <- positive.for.stage
  }
  
  staged.data <- dplyr::select(staged.data, -id)
  
  diffs <- apply(staged.data, 1, diff)
  if (n == 2) {
    increasing <- diffs <= 0
  } else {
    increasing <- apply(diffs <= 0, 2, all)
  }
  
  stage <- ifelse(increasing, rowSums(staged.data), atypical)
  return(stage)
} 