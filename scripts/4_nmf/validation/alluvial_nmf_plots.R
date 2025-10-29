library(dplyr)
library(ggplot2)
library(ggalluvial)
library(tidyr)
library(tools)

ROOT.OUTPUT <- '~/Desktop/atstaging'

amy <- read.csv(file.path(ROOT.OUTPUT, 'plots', 'validation_nmf_similarity', 'amyloid_wta_for_alluvial_data.csv'))
tau <- read.csv(file.path(ROOT.OUTPUT, 'plots', 'validation_nmf_similarity', 'tau_wta_for_alluvial_data.csv'))

colnames(amy) <- c('voxel', 'Training', 'Validation')
colnames(tau) <- c('voxel', 'Training', 'Validation')

a.data <- amy %>%
  pivot_longer(-voxel, names_to = 'Dataset', values_to = 'factor') %>%
  mutate(factor = as.factor(factor)) %>%
  filter(factor != 0)

t.data <- tau %>%
  pivot_longer(-voxel, names_to = 'Dataset', values_to = 'factor') %>%
  mutate(factor = as.factor(factor)) %>%
  filter(factor != 0)

# ===========

odir <- file.path(file.path(ROOT.OUTPUT, 'plots', 'validation_nmf_similarity'))

# amyloid
ggplot(a.data, aes(x=Dataset, stratum=factor, alluvium=voxel, fill=factor, label=factor)) +
  geom_flow(stat='flow', aes.flow = 'forward') +
  geom_stratum(fill='white') +
  theme_light() +
  theme(legend.position = 'none',
        text = element_text(size=8)) +
  ylab('Voxel')

ggsave(file.path(odir, 'amyloid_alluvial.svg'), width = 3, height = 3, units = 'in')

# tau
ggplot(t.data, aes(x=Dataset, stratum=factor, alluvium=voxel, fill=factor, label=factor)) +
  geom_flow(stat='flow', aes.flow = 'forward') +
  geom_stratum(fill='white') +
  theme_light() +
  theme(legend.position = 'none',
        text = element_text(size=8)) +
  ylab('Voxel')

ggsave(file.path(odir, 'tau_alluvial.svg'), width = 3, height = 3, units = 'in')
