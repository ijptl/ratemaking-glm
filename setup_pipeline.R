# 1. Install required packages
if (!require(xts)) install.packages("xts")
if (!require(CASdatasets)) install.packages("CASdatasets", repos = "https://dutangc.perso.math.cnrs.fr/RRepository/pub/", type = "source")
if (!require(tidyverse)) install.packages("tidyverse")
if (!require(DescTools)) install.packages("DescTools")

library(CASdatasets)
library(tidyverse)
library(DescTools)

# 2. Load raw data
data(freMTPL2freq)
data(freMTPL2sev)

# 3. Clean: cap VehAge at 20
freMTPL2freq$VehAge <- pmin(freMTPL2freq$VehAge, 20)

# 4. Merge severity with policy rating factors
sev_merged <- merge(freMTPL2sev, freMTPL2freq, by = "IDpol")

# 5. Fit models
freq_model <- glm(ClaimNb ~ VehPower + VehAge + DrivAge + BonusMalus + VehGas + Area + Region,
                  data = freMTPL2freq,
                  family = poisson(link = "log"),
                  offset = log(Exposure))

sev_model <- glm(ClaimAmount ~ VehPower + VehAge + DrivAge + BonusMalus + VehGas + Area,
                 data = sev_merged,
                 family = Gamma(link = "log"))

# 6. Add predictions/decile columns used in validation
freMTPL2freq$predicted <- predict(freq_model, type = "response")
freMTPL2freq$predicted_rate <- freMTPL2freq$predicted / freMTPL2freq$Exposure
freMTPL2freq$decile <- ntile(freMTPL2freq$predicted_rate, 10)

cat("Pipeline complete. Objects ready: freMTPL2freq, sev_merged, freq_model, sev_model\n")

dir.create("dashboard/data", recursive = TRUE, showWarnings = FALSE)

# lift chart data
write.csv(decile_summary, "dashboard/data/decile_summary.csv", row.names = FALSE)

# relativities from freq model coefs
freq_coefs <- summary(freq_model)$coefficients
relativities <- data.frame(
  factor = rownames(freq_coefs),
  relativity = round(exp(freq_coefs[, "Estimate"]), 4)
)
write.csv(relativities, "dashboard/data/relativities.csv", row.names = FALSE)

# sample rows for premium calculator
sample_predictions <- freMTPL2freq[sample(nrow(freMTPL2freq), 1000), 
                                   c("VehPower", "VehAge", "DrivAge", "BonusMalus", 
                                     "VehGas", "Area", "Region", "predicted_rate")]
write.csv(sample_predictions, "dashboard/data/sample_predictions.csv", row.names = FALSE)

# gini score
write.csv(data.frame(metric = "Gini", value = round(gini_model, 4)), 
          "dashboard/data/gini_score.csv", row.names = FALSE)

