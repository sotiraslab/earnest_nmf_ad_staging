library(colormap)
library(dplyr)
library(ggplot2)
library(scales)
library(stringr)
library(tidyr)

ROOT.OUTPUT <- '~/Desktop/atstaging/'

path <- file.path(ROOT.OUTPUT, 'filesForR', 'maindata.csv')
df <- read.csv(path)
wcols <- colnames(df)[str_detect(colnames(df), '.*WScore')]

# Set data/parameters for plot
train <- df %>% 
  filter(Split == 'TrainingBaseline', ControlForStaging == 'False')

bin.data <- train %>%
  select(all_of(wcols)) %>%
  mutate(across(everything(), function (x) ifelse(x > 2.5, 1, 0)))

colnames(bin.data) <- colnames(bin.data) %>%
  str_replace('WScore', '') %>%
  str_replace('PTC', 'PTC-') %>%
  str_replace('PAC', 'PAC-')

colors <- c('#83c5be', '#006d77', '#004643')

empty.name <- 'Negative'

by <- train$CDRBinned
by[by == ''] <- '0.0'
cats <- c('0.0', '0.5', '1.0+')
by <- factor(by, levels = cats)

# Main

cols <- colnames(bin.data)
if (is.null(cats)) {
  cats <- as.character(sort(unique(df[[by]])))
}
ncats <- length(cats)

# get order of regions
positivity.order <- names(sort(colSums(bin.data), decreasing = T))
bin.data <- bin.data[, positivity.order]

# totals data
totals <- colSums(bin.data)
totals <- data.frame(variable = names(totals), value = unname(totals), Idx=0)

# scale cells with the by column
bin.data <- as.numeric(by) * bin.data
bin.data <- bin.data %>%
  mutate(by = by, .before = 1)

# sort rows to create staircase
bin.data <- bin.data[do.call(order, bin.data), ]

idx <- 1:nrow(bin.data)
bin.data$Idx <- idx

hmap.data <- bin.data %>%
  pivot_longer(cols) %>%
  mutate(name = factor(name, levels=rev(positivity.order)), value = factor(value, labels=c(empty.name, levels(by))))

plotcolors <- list()
plotcolors[[ empty.name ]] <- 'white'
if (is.null(colors)) {
  colors <- colormap('plasma', nshades = ncats)
} 
for (i in 1:ncats) {
  plotcolors[[cats[i]]] <- colors[[i]]
}
# plotcolors <- list(
#   Negative = 'white',
#   '0.0' = c(68, 1, 84),
#   '0.5' = c(68, 1, 84),
#   '1.0+' = c(68, 1, 84)
# )

ggplot() +
  geom_tile(
    data=hmap.data,
    aes(x=Idx, y=name, fill=value, color=value),
    linewidth = 0.1
    ) +
  scale_fill_manual(values = unlist(plotcolors)) +
  scale_colour_manual(values = unlist(plotcolors)) +
  scale_x_reverse(expand = expansion(add = 0)) +
  scale_y_discrete(expand = expansion(add = 0)) +
  theme_bw() +
  theme(
    text = element_text(size=7),
    axis.ticks = element_blank(),
    axis.text.x = element_blank(),
    legend.position = 'none',
    axis.title.y = element_blank()) +
  ylab('Region') +
  xlab('Participant')

odir <- file.path(ROOT.OUTPUT, 'plots', 'stage_development')
ggsave(
  filename = file.path(odir, 'heatmap_training_positivity.svg'),
  width = 7, height = 1.5, units = 'in')