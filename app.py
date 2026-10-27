import streamlit as st

st.set_page_config(
    page_title="Creative Industries Atlas",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

home = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)
business = st.Page("pages/business_counts.py", title="Business Counts", icon=":material/domain:")
intensity = st.Page(
    "pages/creative_business_intensity.py",
    title="Creative Business Intensity",
    icon=":material/percent:",
)
growth = st.Page(
    "pages/creative_industry_growth.py",
    title="Creative Industry Growth",
    icon=":material/trending_up:",
)
employment = st.Page("pages/employment.py", title="Employment", icon=":material/groups:")
turnover = st.Page("pages/turnover.py", title="Turnover", icon=":material/payments:")
employment_bands = st.Page(
    "pages/employment_size_bands.py",
    title="Employment Size Bands",
    icon=":material/bar_chart:",
)

pg = st.navigation(
    {
        "Creative Industries Atlas": [home],
        "Indicators": [
            business,
            intensity,
            growth,
            employment,
            turnover,
            employment_bands,
        ],
    }
)
pg.run()
