import streamlit as st

from atlas.styles import inject_styles

inject_styles()

st.markdown(
    "<div class='atlas-kicker'>UK Creative Economy</div>",
    unsafe_allow_html=True,
)
st.title("Creative Industries Atlas")
st.markdown(
    """
    <div class='atlas-subtitle'>
    Explore the Creative Industries through separate, faster indicator pages.
    Each indicator loads only the data it needs, while sharing the same mapping,
    geography and filtering approach.
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2, gap="large")

with c1:
    st.subheader("Indicators")
    st.page_link("pages/business_counts.py", label="Business Counts", icon="🏢")
    st.page_link(
        "pages/creative_business_intensity.py",
        label="Creative Business Intensity",
        icon="📊",
    )
    st.page_link(
        "pages/creative_industry_growth.py",
        label="Creative Industry Growth",
        icon="📈",
    )
    st.page_link("pages/employment.py", label="Employment", icon="👥")
    st.page_link("pages/turnover.py", label="Turnover", icon="💷")
    st.page_link(
        "pages/employment_size_bands.py",
        label="Employment Size Bands",
        icon="📊",
    )

with c2:
    st.subheader("Geography")
    st.markdown(
        """
        **Countries**
        - United Kingdom
        - England
        - Scotland
        - Wales
        - Northern Ireland

        **Distinct Areas**
        - One Creative North
        - South Central

        **Local Authorities**
        - Choose an individual Local Authority
        """
    )

st.divider()
st.subheader("How the Atlas works")
st.markdown(
    """
    Every indicator page uses the same Creative Industries and Geography
    approach. Turnover and Employment Size Bands also include their relevant
    band filter.

    **Creative Business Intensity** measures selected Creative Industries
    enterprises as a percentage of all enterprises in each Local Authority,
    using the all-industry denominator from the same NOMIS Business Counts extract.

    **Creative Industry Growth** compares Creative Industries enterprise counts
    between two selected years and maps percentage change by Local Authority.

    **Employment** uses NOMIS BRES data for 2015–2024 and shows Employees,
    Full-time employees and Part-time employees. BRES covers Great Britain,
    so Northern Ireland is not available on that page.

    Maps use the existing Pydeck design. Hovering over an area shows the
    **Local Authority**, **Region**, **Geography**, **Year/period** and the
    selected indicator value.
    """
)
