
library(colormap)
library(dplyr)
library(ggplot2)
library(ggalluvial)
library(stringr)
library(tibble)
library(tidyr)

ROOT.OUTPUT <-'/Users/earnestt1234/Desktop/atstaging'
PLOT.SMAX <- 7

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'stability')
dir.create(odir, showWarnings = F)

path.data <- file.path(ROOT.OUTPUT, 'filesForR', 'training_alluvial_subtype_data.csv')
df <- read.csv(path.data)[, 1:(PLOT.SMAX + 1)]

na.color <- c('NA'='gray')
s.color <- colormap::colormap('viridis', nshades = 7)
names(s.color) <- str_c('S', 1:7)
colors <- c(na.color, s.color)

p.data <- df %>%
  pivot_longer(cols = -Index, names_to = 'ModelName', values_to = 'Subtype') %>%
  mutate(`N Subtypes` = factor(str_extract(ModelName, '\\d+'), levels=as.character(1:10)),
         Subtype = ifelse(Subtype == 0, 'NA', str_c('S', Subtype)))

ggplot(p.data, aes(x = `N Subtypes`, stratum = Subtype, alluvium = Index, fill = Subtype, label = Subtype)) +
  geom_flow(stat = "flow", aes.flow='backward') +
  geom_stratum() +
  theme_bw() +
  scale_y_continuous(expand = c(0, 0.005)) +
  scale_x_discrete(expand = c(0.13, 0.13)) +
  theme(
    text = element_text(size = 14)
  ) +
  scale_fill_manual(values = colors) + 
  ylab('Subject')

ggsave(file.path(odir, 'alluvial_across_nsubtypes_training.svg'), width = 6, height = 6, units = 'in')

# === Some sort of statistic? ========

start <- 2
end <- 7

my.mode <- function(x) {
  ux <- unique(x)
  ux[which.max(tabulate(match(x, ux)))]
}

final.data <- rep(NA, 7)

for (i in start:end) {
  col.current <- sprintf('n_subtypes_%s', i)
  col.prev <- sprintf('n_subtypes_%s', i-1)
  
  s.unique <- sort(unique(df[[col.current]]))
  n.unique <- length(s.unique)
  data.for.subtype <- rep(NA, n.unique)
  
  for (j in 1:n.unique) {
    s <- s.unique[j]
    prev.subtypes <- df[df[[col.current]] == s, col.prev]
    m <- my.mode(prev.subtypes)
    data.for.subtype[j] <- mean(prev.subtypes == m)
  }
  final.data[i] <- mean(data.for.subtype)
}

# === grouping over time =======

anchor.subtype <- 3
start <- 1
end <- 7

anchor.col <- sprintf('n_subtypes_%s', anchor.subtype)

unique.anchor <- sort(unique(df[[anchor.col]]))
n.unique.anchor <- length(unique.anchor)

result <- matrix(NA,  nrow = n.unique.anchor, ncol = 7)

for (i in start:end) {
  for (j in 1:n.unique.anchor) {
    anchor.subtype <- unique.anchor[j]
    mask <- df[[anchor.col]] == anchor.subtype
    anchor.data <- df[mask, anchor.col]
    
    compare.col <- sprintf('n_subtypes_%s', i)
    compare.data <- df[mask, compare.col]
    table.compare.data <- table(compare.data)
    
    result[j, i] <- max(table.compare.data ) / sum(table.compare.data )
  }
}

p.data <- as.data.frame(result)
colnames(p.data) <- 1:7
row.names(p.data) <- c('NA', 'S1', 'S2', 'S3')
p.data <- p.data %>%
  rownames_to_column('Subtype') %>%
  pivot_longer(-Subtype, names_to = 'N Subtypes', values_to = 'ProportionTogether')

colors <- c(
  'NA' = 'gray',
  'S1' = '#db2b39',
  'S2' = '#053c5e',
  'S3' = '#f3a712' 
)

ggplot(data = p.data, aes(x = `N Subtypes`, y = ProportionTogether, fill = Subtype, color=Subtype, group = Subtype)) + 
  geom_line() + 
  scale_color_manual(values = colors) +
  geom_point(size=3) + 
  theme_bw() + 
  theme(text = element_text(size = 14)) + 
  scale_y_continuous(limits = c(0, 1.0)) +
  ylab('Consistent subtype assignment')

ggsave(file.path(odir, 'consistent_subtype_assignment_s3_training.svg'), width = 6, height = 6, units = 'in')