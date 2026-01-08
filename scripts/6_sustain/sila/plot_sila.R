library(dplyr)
library(gt)
library(gtsummary)
library(lubridate)
library(stringr)
library(this.path)

# Set where to find files
ROOT.OUTPUT <- '/Users/earnestt1234/Desktop/atstaging/'

odir <- file.path(ROOT.OUTPUT, 'plots', 'sustain', 'sila')
dir.create(odir, showWarnings = F)

# Load ANOVA helper funcs
path.anova <- normalizePath(file.path(this.dir(), '..', '..', 'rsource', 'anova.R'))
source(path.anova)

# Load data
PATH.DATA <- file.path(ROOT.OUTPUT, 'filesForR', 'master_with_sustain.csv')
PATH.OUTPUT <- file.path(ROOT.OUTPUT, 'tables')
dir.create(PATH.OUTPUT, showWarnings = F)

master <- read.csv(PATH.DATA)
master$TauAmyloidMeanDate <- as_datetime(ymd_hms(master$TauAmyloidMeanDate))
master$Subtype <- ifelse(master$ControlForStaging == "True", 'Control', master$TrainingMLSubtype)

# load SILA
s1.path <- file.path(ROOT.OUTPUT, 'sila', 'output', 's1_SILA_estimates.csv')
s2.path <- file.path(ROOT.OUTPUT, 'sila', 'output', 's2_SILA_estimates.csv')
s3.path <- file.path(ROOT.OUTPUT, 'sila', 'output', 's3_SILA_estimates.csv')

s1 <- read.csv(s1.path)
s2 <- read.csv(s2.path)
s3 <- read.csv(s3.path)
join <- bind_rows(s1, s2, s3)

master <- left_join(master, join, by = c('Subject', 'Session')) %>%
  mutate(
    DiffEAO = ifelse(
      Subtype == 'S2',
      EstAgeOnsetPTCOccipitalWScore - EstAgeOnsetPACParietalWScore,
      EstAgeOnsetPTCMedialTemporalWScore - EstAgeOnsetPACFrontalWScore
    )
  )

# data selection
training.subs <- master %>%
  filter(
    Split == 'TrainingBaseline',
    ControlForStaging == "False",
    TrainingMLStage != 0,
    TrainingSubtypeValid ==1 
  ) %>%
  pull(Subject)

training.bl <- master %>%
  filter(Subject %in% training.subs, str_detect(Split, 'Baseline'))
training.long <- master %>%
  filter(Subject %in% training.subs)

# === Plot/ANOVA ======

cols <- c(
  "EstAgeOnsetPACFrontalWScore",
  "EstAgeOnsetPACParietalWScore",
  "EstAgeOnsetPTCMedialTemporalWScore",
  "EstAgeOnsetPTCOccipitalWScore"
)

colors <- c(
  'Control' = 'gray',
  'S1' = '#db2b39',
  'S2' = '#053c5e',
  'S3' = '#f3a712'
)


p.data <- training.bl %>%
  select(Subtype, all_of(cols)) %>%
  pivot_longer(all_of(cols), names_to = 'Region', values_to = 'EAO') %>%
  mutate(
    Region = str_replace(Region, 'EstAgeOnset', ''),
    Region = str_replace(Region, 'WScore', ''),
    Region = str_replace(Region, 'PTC', 'PTC-'),
    Region = str_replace(Region, 'PAC', 'PAC-')
  )

p <- ggplot(p.data, aes(x=Region, y=EAO, fill=Subtype)) +
  geom_boxplot(color='black') +
  scale_fill_manual(values = colors) +
  theme_bw() +
  theme(text = element_text(size = 6)) +
  scale_y_continuous(breaks = c(50, 60, 70, 80, 90, 100))

xmin <- c(-0.3, -0.3, 0)
xmax <- c(0, 0.3, 0.3)

for (i in 1:length(cols)) {
  col <- cols[i]
  output <- my.anova(x = 'Subtype', y = col, data = training.bl)
  posthoc <- output$posthoc
  
  # save posthoc
  path.stats <- file.path(odir, sprintf('anova_posthoc_%s.csv', col))
  write.csv(posthoc, path.stats, row.names = F)
  
  for (j in 1:nrow(posthoc)) {
    annot <- posthoc[j, 'annotation']
    
    # no significance, don't draw bar
    if (! str_detect(annot, '\\*')) {
      next
    }
    
    # significance, draw bar
    p <- p + geom_signif(
      y_position = 100 + (j * 4),
      xmin = i + xmin[j],
      xmax = i + xmax[j],
      annotation = annot,
      tip_length = .01,
      size = 0.5,
      textsize = 3
      ) 
  }
}

print(p)
path.plot <- file.path(odir, sprintf('eao_boxplot.svg'))
ggsave(path.plot, width = 4, height = 3, units = 'in')

# Plot EAO tau/amyloid =======
source(path.anova)

result <- anova.plot(
  x = 'Subtype', y = 'DiffEAO', data = training.bl,
  colors = colors,
  sig.y.start = 25, sig.y.gap = 3,
  point.size = 2, point.linewidth = .5,
  stat.textsize=3, stat.size=.5
  )
p <- result$plot +
  geom_hline(yintercept = 0, color = 'black', linetype='dashed') +
  theme_bw() + 
  theme(text = element_text(size = 6),
        legend.position = 'none') +
  ylab('Tau EAO - Amyloid EAO') +
  scale_y_continuous(breaks = seq(-25, 25, 5))

print(p)
path.plot <- file.path(odir, sprintf('eao_tau_amyloid_difference.svg'))
ggsave(path.plot, width = 2, height = 3, units = 'in')


# ==== Plot against model ======

subtypes <- c('S1', 'S2', 'S3')
regions <- c(
  "PACFrontalWScore",
  "PACParietalWScore",
  "PTCMedialTemporalWScore",
  "PTCOccipitalWScore"
)

sub.odir <- file.path(odir, 'modelcurves')
dir.create(sub.odir, showWarnings = F)

for (i in 1:length(subtypes)) {
  for (j in 1:length(regions)) {
    subtype <- subtypes[i]
    region <- regions[j]
    curve.data.path <- file.path(ROOT.OUTPUT, 'sila', 'output', sprintf('%s_%s_curve.csv', tolower(subtype), region))
    curve <- read.csv(curve.data.path)
    
    eao.col <- sprintf('EstAgeOnset%s', region)
    tmp <- training.long %>% filter(Subtype == subtype)
    pdata <- data.frame(sub = tmp[['Subject']], x = tmp[['Age']] - tmp[[eao.col]], y = tmp[[region]])
    
    color = colors[[subtype]]
    ggplot(data = pdata, aes(x = x, y = y, group = sub)) +
      geom_line(color = color, alpha = 0.5) +
      geom_point(color = color, alpha = 0.5) +
      geom_ribbon(data = curve, aes(x = adtime, ymin = val - ci95, ymax = val + ci95), inherit.aes = F, fill = 'gray', alpha = 0.7) +
      geom_line(data = curve, aes(x = adtime, y = val), inherit.aes = F, color = 'black', linewidth = 1) +
      geom_hline(yintercept = 2.5, linetype = 'dashed') + 
      theme_bw() +
      theme(text = element_text(size = 14)) + 
      ylab(region) + 
      xlab('Years to estimated onset')
    
    opath <- file.path(sub.odir, sprintf("%s_%s.svg", subtype, region))
    ggsave(opath, width = 8, height = 6, units = 'in')
  }
}


