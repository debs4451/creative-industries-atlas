import streamlit as st

from atlas.ui import inject_styles

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
    Every indicator page uses the same controls for **Year**, **Creative
    Industries** and **Geography**. Turnover and Employment Size Bands also
    include their relevant band filter.

    Maps use the existing Pydeck design. Hovering over an area now shows the
    **Local Authority**, **Region**, **Geography**, **Year** and the selected
    indicator value.

    The app caches data and map boundaries and keeps indicator datasets on
    separate pages, so opening Turnover does not also load Business Counts or
    Employment Size Bands.
    """
)
