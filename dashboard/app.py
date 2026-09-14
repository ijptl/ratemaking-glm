import streamlit as st
import pandas as pd
import plotly.express as px
import os

# load data from base direct
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

decile_df = pd.read_csv(os.path.join(BASE_DIR, "data", "decile_summary.csv"))
relativities_df = pd.read_csv(os.path.join(BASE_DIR, "data", "relativities.csv"))
sample_df = pd.read_csv(os.path.join(BASE_DIR, "data", "sample_predictions.csv"))
gini_df = pd.read_csv(os.path.join(BASE_DIR, "data", "gini_score.csv"))

gini_value = gini_df["value"].iloc[0]

# sidebar summary
st.sidebar.header("Project Summary")
st.sidebar.metric("Policies Analyzed", "677,991")
st.sidebar.metric("Claims Analyzed", "26,444")
st.sidebar.metric("Model Gini", gini_value)

tab1, tab2 = st.tabs(["Dashboard", "Full Report"])
with tab1:
    st.title("Motor Insurance Ratemaking Dashboard")
    st.write("A GLM-based pricing model for the French Motor Third-Party Liability dataset.")

    with st.expander("About this project"):
        st.markdown("""
        This dashboard presents an actuarial ratemaking model built on the French Motor 
        Third-Party Liability dataset (677K+ policies, 26K+ claims). It uses separate 
        Poisson and Gamma GLMs to model claim **frequency** and **severity**, then combines 
        them into risk-based pricing.

        **Tech stack:** R (GLM modeling, validation) → Python/Streamlit (this dashboard)  
        **Code & methodology:** [GitHub repo](https://github.com/ijptl/ratemaking-glm)
        """)

    with st.expander("Preview the underlying data"):
        st.dataframe(sample_df.head(20))

    col1, col2 = st.columns(2)
    col1.metric("Model Gini Coefficient", gini_value)
    col2.metric("Baseline Gini", "~0.00")

    st.subheader("Model Validation: Predicted vs. Actual Claim Rate")

    fig_lift = px.line(
        decile_df,
        x="decile",
        y=["avg_predicted", "avg_actual"],
        markers=True,
        labels={"decile": "Risk Decile", "value": "Claim Rate", "variable": "Series"},
        title="Lift Chart by Risk Decile"
    )
    st.plotly_chart(fig_lift)

    st.subheader("Rate Relativity Explorer")

    # clean up factor names for display
    relativities_df["factor_clean"] = relativities_df["factor"].str.replace(
        r"(VehPower|VehAge|DrivAge|BonusMalus|VehGasRegular|Area|Region)", r"\1: ", regex=True
    )

    factor_groups = st.selectbox(
        "Choose a rating factor to explore",
        ["Area", "Region", "VehGas"]
    )

    filtered = relativities_df[relativities_df["factor"].str.contains(factor_groups)]

    fig_rel = px.bar(
        filtered,
        x="factor",
        y="relativity",
        labels={"factor": "Category", "relativity": "Rate Relativity"},
        title=f"Relativities: {factor_groups}"
    )
    fig_rel.add_hline(y=1, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_rel)

    st.subheader("What Drives Risk Most?")
    # only keep statistically significant factors (p < 0.05) so the
    # ranking isn't skewed by noisy, unreliable coefficients (e.g. Region)
    top_factors = relativities_df[
        (relativities_df["factor"] != "(Intercept)") &
        (relativities_df["p_value"] < 0.05)
    ].copy()
    top_factors["abs_effect"] = (top_factors["relativity"] - 1).abs()
    top_factors = top_factors.nlargest(10, "abs_effect")
    fig_importance = px.bar(top_factors, x="abs_effect", y="factor", orientation="h",
                              title="Top Statistically Significant Rating Factors")
    st.plotly_chart(fig_importance)
    st.caption(
        "Only includes factors significant at p < 0.05 in the frequency model. "
        "Note: continuous variables (VehPower, VehAge, DrivAge, BonusMalus) show the effect of "
        "one unit of change, so they may rank lower here even when highly significant — "
        "this chart measures effect size, not statistical significance."
    )

    st.subheader("Premium Calculator")

    col1, col2, col3 = st.columns(3)
    veh_power = col1.slider("Vehicle Power", 4, 15, 7)
    veh_age = col2.slider("Vehicle Age", 0, 20, 5)
    driv_age = col3.slider("Driver Age", 18, 90, 40)

    col4, col5 = st.columns(2)
    bonus_malus = col4.slider("Bonus-Malus Score", 50, 200, 100)
    area = col5.selectbox("Area", ["A", "B", "C", "D", "E", "F"])

    # base rate is the average predicted rate across the whole book
    base_rate = sample_df["predicted_rate"].mean()

    # pull relativities for the selected inputs
    def get_relativity(factor_name):
        match = relativities_df[relativities_df["factor"] == factor_name]
        if len(match) > 0:
            return match["relativity"].iloc[0]
        return 1.0

    area_rel = get_relativity(f"Area{area}") if area != "A" else 1.0
    power_effect = relativities_df[relativities_df["factor"] == "VehPower"]["relativity"].iloc[0] ** veh_power
    age_effect = relativities_df[relativities_df["factor"] == "VehAge"]["relativity"].iloc[0] ** veh_age
    driv_effect = relativities_df[relativities_df["factor"] == "DrivAge"]["relativity"].iloc[0] ** driv_age
    bm_effect = relativities_df[relativities_df["factor"] == "BonusMalus"]["relativity"].iloc[0] ** bonus_malus

    estimated_rate = base_rate * area_rel * power_effect * age_effect * driv_effect * bm_effect

    st.metric("Estimated Annual Claim Frequency", f"{estimated_rate:.3f}")
    st.caption("This is a simplified illustrative estimate combining individual rate relativities, not the full model output.")

with tab2:
    st.header("Methodology Report")
    with open(os.path.join(BASE_DIR, "WriteUp.html"), "r", encoding="utf-8") as f:
        html_content = f.read()
    st.components.v1.html(html_content, height=1000, scrolling=True)