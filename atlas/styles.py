import streamlit as st


def inject_styles():
    """Lightweight shared styling.

    Kept in its own module so the Home page does not import pandas, Plotly,
    Pydeck, or the map/data stack during cold start.
    """
    st.markdown(
        """
        <style>
        .block-container {
            padding: 1rem 1.35rem 2.5rem 1.35rem;
            max-width: 1800px;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid #dde3e7;
        }
        [data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
        }
        h1 {
            font-size: 2.0rem !important;
            letter-spacing: -.02em;
            margin-bottom: .15rem !important;
        }
        h2, h3 { letter-spacing: -.01em; }
        .atlas-kicker {
            font-size:.76rem;
            text-transform:uppercase;
            letter-spacing:.12em;
            font-weight:700;
            color:#50616a;
            margin-bottom:.15rem;
        }
        .atlas-subtitle {
            font-size:1rem;
            color:#53636c;
            margin-bottom:1rem;
            max-width:950px;
        }
        .metric-card {
            border:1px solid #dfe5e8;
            border-radius:12px;
            padding:14px 16px;
            background:#fff;
            min-height:92px;
        }
        .metric-label {
            font-size:.76rem;
            text-transform:uppercase;
            letter-spacing:.06em;
            color:#66747c;
        }
        .metric-value {
            font-size:1.55rem;
            font-weight:700;
            color:#12262f;
            margin-top:2px;
        }
        .detail-card {
            border:1px solid #dfe5e8;
            border-radius:14px;
            padding:16px 18px;
            background:#fff;
        }
        .detail-title {
            font-size:1.2rem;
            font-weight:700;
            color:#12262f;
            margin-bottom:.15rem;
        }
        .detail-meta {
            font-size:.88rem;
            color:#61717a;
            margin-bottom:.85rem;
        }
        .detail-row {
            display:flex;
            justify-content:space-between;
            gap:18px;
            padding:8px 0;
            border-top:1px solid #edf0f2;
            font-size:.92rem;
        }
        .detail-row b { color:#12262f; }
        .small-note { font-size:.82rem; color:#6b7880; }
        div[data-testid="stDownloadButton"] button { width:100%; }
        .stPlotlyChart {
            border:1px solid #edf0f2;
            border-radius:12px;
            overflow:hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
