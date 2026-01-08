library(dplyr)
library(ggplot2)
library(tidyr)

stacked.barplot <- function(df, xcol, ycol, levels=NULL, colors=NULL,
                            return.data = F, dropna = F, annotate = F,
                            annotate.color = 'black',
                            annotate.size = 6, annotation.minsize = 0,
                            toptext.size = 6) {
  
  # create data
  if (dropna) {
    df <- df[! is.na(df[[xcol]]), ]
    df <- df[! is.na(df[[ycol]]), ]
  }
  
  plot.data <- df %>%
    group_by_at(c(xcol, ycol)) %>%
    summarise(N=n())
  
  if (! is.null(levels)) {
    plot.data <- filter(plot.data, !!sym(xcol) %in% levels)
  }
  plot.data <- plot.data %>%
    ungroup() %>%
    group_by(!!sym(xcol)) %>%
    mutate(Percent = N / sum(N) * 100)
  
  if (return.data) {
    return (plot.data)
  }
  
  # annotations
  x.order <- sort(unique(plot.data[[xcol]]))
  y.order <- sort(unique(plot.data[[ycol]]))
  annot.data <- plot.data %>%
    mutate(XFactor = factor(!!sym(xcol), levels = x.order),
           YFactor = factor(!!sym(ycol), levels = rev(y.order))) %>%
    arrange(XFactor, YFactor) %>%
    mutate(AnnotX = as.integer(XFactor)) %>%
    group_by(XFactor) %>%
    mutate(AnnotYMax = cumsum(Percent),
           AnnotYMin = AnnotYMax - Percent,
           AnnotY = (AnnotYMin + AnnotYMax) / 2,
           Annot = str_c(round(Percent, 2), '%'),
           Annot = ifelse((AnnotYMax - AnnotYMin) < annotation.minsize, '', Annot)
           )
  
  # try to spread out some of the annotations
  # if (! is.null(annotation.closeness)) {
  #   for (x in x.order) {
  #     mask <- annot.data[[xcol]] == x
  #     yloc <- annot.data[mask, 'AnnotY', drop = T]
  #     too.close <- diff(yloc) < annotation.closeness
  #     
  #     # all are far enough apart
  #     if (! any(too.close)) {
  #       next
  #     }
  #     
  #     # some are too close, move
  #     annot.data[mask, 'AnnotY'] <- ifelse(c(F, too.close), yloc + (annotation.closeness/2), yloc)
  #     annot.data[mask, 'AnnotY'] <- ifelse(c(too.close, F), yloc - (annotation.closeness/2), annot.data[mask, 'AnnotY', drop = T])
  #   }
  # }
  
  # get totals for text
  group.sums <- plot.data %>%
    group_by(!!sym(xcol)) %>%
    summarise(total=sum(N)) %>%
    ungroup()
  
  # plot
  p <- ggplot() +
    geom_bar(data = plot.data, aes(fill=!!sym(ycol), y=Percent, x=!!sym(xcol)), stat="identity", color='black') +
    geom_text(data = group.sums, aes(x=!!sym(xcol), y=105, label=total), size=toptext.size) +
    theme_classic() +
    ylab('Observations (%)') +
    xlab(xcol) +
    scale_y_continuous(expand=expansion(mult=c(0, .1)), breaks = c(0, 25, 50, 75, 100)) +
    guides(fill=guide_legend(title=ycol)) +
    theme(text = element_text(size=20),
          axis.line.y = element_blank()) +
    geom_segment(aes(y=0,yend=100,x=-Inf,xend=-Inf), color='black', linewidth=1)
  
  if (annotate) {
    p <- p + geom_text(
      data = annot.data,
      aes(x = AnnotX, y = AnnotY, label = Annot),
      inherit.aes = F,
      color = annotate.color,
      size = annotate.size)
  }
  
  if (! is.null(colors)) {
    p <- p + scale_fill_manual(values=colors)
  }
  
  return(p)
}