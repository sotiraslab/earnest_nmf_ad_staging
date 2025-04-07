
# ----- IMPORTS ------
library(anticlust)
library(argparse)
library(this.path)

# ----- PARSE -------

parse <- function(args=NULL) {
  parser <- ArgumentParser()
  parser$add_argument('inpath')
  parser$add_argument('outpath')
  parser$add_argument('-K', '--n-splits', dest='K', default=2, type='integer')
  parser$add_argument('-N', '--n-repeats', dest='N', default=15, type='integer')
  parser$add_argument('--id', dest='id.columns', nargs='+', default=c('Subject', 'Session'))
  parser$add_argument('--continuous', dest='continuous.columns', nargs='+', default=c('Age', 'SummarySUVRAmyloid', 'SummarySUVRTau'))
  parser$add_argument('--categorical', dest='categorical.columns', nargs='+', default=c('DataSet', 'CDRBinned', 'SexMale'))
  parser$add_argument('-q', '--quiet', dest='verbose', action='store_false')
  parser$add_argument('-s', '--seed', default=42, type='integer')
  
  args <- if (is.null(args)) commandArgs(T) else args
  result <- parser$parse_args(args)
  return (result)
}


# ---- MAIN -----

my.print <- function(x=NULL) {
  if (is.null(x)) {
    x <- ''
  }
  to.print <- paste(x, '\n', sep='')
  cat(to.print)
}

main <- function(inpath, outpath, K, N,
                 id.columns = c('Subject', 'Session'),
                 continuous.columns = c('Age', 'SummarySUVRAmyloid', 'SummarySUVRTau'),
                 categorical.columns = c('DataSet', 'CDRBinned', 'SexMale'),
                 verbose = T, seed = NULL) {
  
  vprint <- if(verbose) my.print else function(x) invisible(NULL)
  dfprint <- if(verbose) print else function(x) invisible(NULL)
  
  vprint()
  vprint('D A T A /// S P L I T T I N G')
  vprint('-----------------------------')
  
  vprint()
  vprint(sprintf('Inpath: %s', inpath))
  vprint(sprintf('Outpath: %s', outpath))
  vprint(sprintf('K [# of splits]: %s', K))
  vprint(sprintf('N [# of repeats]: %s', N))
  vprint(sprintf('ID columns: %s', paste(id.columns, collapse=' ')))
  vprint(sprintf('Continuous Columns: %s', paste(continuous.columns, collapse=' ')))
  vprint(sprintf('Categorical Columns: %s', paste(categorical.columns, collapse=' ')))
  vprint(sprintf('Random seed: %s', seed))
  
  vprint()
  vprint('BEGIN')
  
  vprint()
  vprint('> Setting random seed.')
  set.seed(seed)
  
  vprint('> Loading input dataset.')
  df <- read.csv(inpath)
  
  vprint('> Constructing output matrix.')
  splits <- matrix(data=NA, nrow=nrow(df), ncol=N)
  
  vprint('> MAIN LOOP')
  continuous.input <- df[, continuous.columns]
  categorical.input <- df[, categorical.columns]
  for (i in 1:N) {
    vprint(sprintf('    + Split #%s/%s', i, N))
    v <- anticlustering(
      x = continuous.input,
      K = K,
      categories = categorical.input
    )
    splits[, i] <- v
  }
  vprint('> COMPLETE')
  
  vprint('> Construction output table.')
  splits <- as.data.frame(splits)
  colnames(splits) <- paste('Split', 1:N, sep = '')
  
  if (! is.null(id.columns)) {
    ids <- df[, id.columns]
    splits <- cbind(ids, splits)
  }
  
  vprint('> Saving output.')
  write.table(splits, outpath, row.names = F, col.names = T, sep = ',')
  vprint(sprintf('> Done [%s].', outpath))
  
  # ----- REPORT ------
  
  report.continuous <- function(x, splits, K, N) {
    result <- matrix(data=NA, nrow=N, ncol=K*2)
    for (i in 1:N) {
      col <- paste('Split', i, sep='')
      v <- splits[[col]]
      for (k in 1:K) {
        mask <- v == k
        x.split <- x[mask]
        x.split.mean <- mean(x.split)
        x.split.sd <- sd(x.split)
        result[i, k] <- x.split.mean
        result[i, K + k] <- x.split.sd
      }
    }
    result <- as.data.frame(result)
    rownames(result) <- paste('Split', 1:N, sep = '')
    colnames(result) <- c(paste('K', 1:K, 'Mean', sep = ''), paste('K', 1:K, 'SD', sep = ''))
    
    return (result)
  }
  
  report.categorical <- function(x, splits, K, N) {
    levels <- unique(x)
    L <- length(levels)
    result <- matrix(data=NA, nrow=N, ncol=K*levels)
    for (i in 1:N) {
      col <- paste('Split', i, sep='')
      v <- splits[[col]]
      for (k in 1:K) {
        mask <- v == k
        x.split <- x[mask]
        for (l in 1:L) {
          level <- levels[l]
          count.l <- sum(x.split == level)
          result[i, (l * (k-1)) + l] 
        }
      }
    }
    result <- as.data.frame(result)
    rownames(result) <- paste('Split', 1:N, sep = '')
    a <- rep('K', K * L)
    b <- rep(1:K, rep(L, K))
    c <- rep(levels, K)
    colnames(result) <- paste(a, b, '_', c, sep='')
    
    return (result)
  }
  
  report.categorical <- function(x, splits, K, N) {
    levels <- unique(x)
    L <- length(levels)
    final.columns <- rep(NA, K*L)
    result <- matrix(data=NA, nrow=N, ncol=K*L)
    for (i in 1:N) {
      col <- paste('Split', i, sep='')
      v <- splits[[col]]
      for (k in 1:K) {
        mask <- v == k
        x.split <- x[mask]
        for (l in 1:L) {
          level <- levels[l]
          count.l <- sum(x.split == level)
          col.index <- (l-1) * K + k
          result[i, col.index] <- count.l
          
          # only populate the column names on the first try
          # these can be determined post-hoc but a little more explicit this way
          if (i == 1) {
            final.columns[col.index] <- paste('K', k, '_', level, sep='')
          }
        }
      }
    }
    result <- as.data.frame(result)
    rownames(result) <- paste('Split', 1:N, sep = '')
    colnames(result) <- final.columns
    
    return (result)
  }
  
  vprint()
  vprint('MATCHING REPORT')
  vprint('---------------')
  
  vprint()
  vprint('*** CONTINUOUS VARIABLES*** ')
  
  # continuous
  for (col in continuous.columns) {
    
    x <- df[[col]]
    
    vprint()
    vprint('========================')
    vprint(col)
    vprint('========================')
    vprint()
    vprint(sprintf('Overall mean: %s', mean(x)))
    vprint(sprintf('Overall SD: %s', sd(x)))
    
    report <- report.continuous(x, splits, K=K, N=N)
    vprint()
    dfprint(report)
  }
  
  vprint()
  vprint('*** CATEGORICAL VARIABLES*** ')
  
  
  # categorical
  for (col in categorical.columns) {
    
    x <- df[[col]]
    
    vprint()
    vprint('========================')
    vprint(col)
    vprint('========================')
    vprint()
    vprint(sprintf('Levels: %s', paste(unique(x), collapse=' ')))
    
    report <- report.categorical(x, splits, K=K, N=N)
    vprint()
    dfprint(report)
  }
}

# ---- RUN -----

args <- parse()
do.call(main, args)

