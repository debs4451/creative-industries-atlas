"""Creative Education & Talent | Creative Industries Atlas
Place in pages/creative_education_talent.py.
Inputs in data/: creative_graduate_outcomes_with_computing.csv, university_locations.csv.
All geography describes PROVIDER reference locations, not graduate jobs or residence.
"""
from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Creative Education & Talent", page_icon="🎓", layout="wide")
ROOT = Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name == 'pages' else Path(__file__).resolve().parent
SUBJECTS = {
    "11 Computing": "Computing",
    "13 Architecture, building and planning": "Architecture, building & planning",
    "24 Media, journalism and communications": "Media, journalism & communications",
    "25 Design, and creative and performing arts": "Design, creative & performing arts",
}
EMPLOYED_ACTIVITIES = ['Full-time employment', 'Part-time employment', 'Unknown pattern of employment', 'Employment and further study']
SOUTH_CENTRAL = {
    'Basingstoke and Deane', 'Hart', 'Rushmoor', 'Test Valley', 'Winchester',
    'Guildford', 'Waverley', 'Woking', 'Bournemouth', 'Poole', 'Christchurch',
    'Bournemouth, Christchurch and Poole', 'BCP', 'Portsmouth', 'Southampton',
    'Isle of Wight', 'East Hampshire', 'Eastleigh', 'Fareham', 'Gosport',
    'Havant', 'New Forest'
}
NORTHERN_REGIONS = {'North East', 'North West', 'Yorkshire and The Humber', 'Yorkshire and the Humber'}
COUNTRY_NAMES = {'Scotland': 'Scotland', 'Wales': 'Wales', 'Northern Ireland': 'Northern Ireland'}

def path_to(name):
    for p in (ROOT / 'data' / name, ROOT / name, ROOT / 'assets' / name):
        if p.exists():
            return p
    return None

@st.cache_data(show_spinner=False)
def read_outcomes(file):
    d = pd.read_csv(file, dtype={'UKPRN': 'string'}, low_memory=False)
    d['UKPRN'] = d['UKPRN'].str.replace(r'\.0$', '', regex=True)
    d['Number'] = pd.to_numeric(d['Number'], errors='coerce').fillna(0)
    d['Subject_label'] = d['Subject'].map(SUBJECTS)
    return d[d['Subject_label'].notna() & d['UKPRN'].notna() & d['Provider'].ne('Total')].copy()

@st.cache_data(show_spinner=False)
def read_locations(file):
    d = pd.read_csv(file, dtype={'UKPRN': 'string'})
    d['UKPRN'] = d['UKPRN'].str.replace(r'\.0$', '', regex=True)
    d = d.rename(columns={'latitude': 'Latitude', 'longitude': 'Longitude',
                          'lat': 'Latitude', 'lon': 'Longitude', 'Local Authority': 'Local_Authority'})
    for c in ['City', 'Region', 'Local_Authority', 'Provider']:
        if c not in d:
            d[c] = pd.NA
    for c in ['Latitude', 'Longitude']:
        d[c] = pd.to_numeric(d[c], errors='coerce') if c in d else float('nan')
    d['Country'] = d['Region'].map(COUNTRY_NAMES)
    d.loc[d['Region'].notna() & d['Country'].isna(), 'Country'] = 'England'
    # An approximate reference city does not establish an individual London borough.
    d['Local_Authority'] = d['Local_Authority'].astype('string')
    d.loc[d['Region'].eq('London') & d['Local_Authority'].isna(), 'Local_Authority'] = 'London (borough not specified)'
    return d.drop_duplicates('UKPRN')

def get_ocn_local_authorities():
    """Read the Atlas's existing exact OCN_ALL if accessible; never invent a list."""
    for p in [ROOT, ROOT / 'pages']:
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    try:
        from config import OCN_ALL
        if isinstance(OCN_ALL, dict):
            vals = []
            for v in OCN_ALL.values():
                if isinstance(v, (list, set, tuple)):
                    vals.extend(v)
                elif isinstance(v, str):
                    vals.append(v)
            return {str(v).strip().casefold() for v in vals}
        if isinstance(OCN_ALL, (list, set, tuple)):
            return {str(v).strip().casefold() for v in OCN_ALL}
    except (ImportError, AttributeError, TypeError):
        pass
    return set()


def make_summary(data, group_cols):
    if data.empty:
        return pd.DataFrame(columns=[*group_cols, 'Graduates', 'Respondents', 'Employed', 'Employment_pct_respondents'])
    v = data.pivot_table(index=group_cols, columns='Activity', values='Number', aggfunc='sum', fill_value=0).reset_index()
    for c in ['Total', 'Total with known outcomes', *EMPLOYED_ACTIVITIES]:
        if c not in v:
            v[c] = 0.
    v['Graduates'] = v['Total']
    v['Respondents'] = v['Total with known outcomes']
    v['Employed'] = v[EMPLOYED_ACTIVITIES].sum(axis=1)
    v['Employment_pct_respondents'] = 100 * v['Employed'].div(v['Respondents'].replace(0, float('nan')))
    return v

outpath, locpath = path_to('creative_graduate_outcomes_with_computing.csv'), path_to('university_locations.csv')
st.title('🎓 Creative Education & Talent')
st.caption('HESA Graduate Outcomes, 2017/18–2023/24 | Computing, Architecture, Media and Design / Performing Arts')
st.info('Geography refers to the **university/provider location**, not where graduates work. These are **graduate employment outcomes**, not evidence of local talent retention. Computing and Architecture include some non-creative courses.')
if outpath is None or locpath is None:
    st.error('Missing files in data/: creative_graduate_outcomes_with_computing.csv and/or university_locations.csv')
    st.stop()

df, locations = read_outcomes(str(outpath)), read_locations(str(locpath))
all_years = sorted(df['Academic_year'].dropna().unique().tolist())

# Filter sidebar — these controls apply to every chart, table and map.
st.sidebar.header('🎓 Creative Education & Talent')
st.sidebar.caption('All charts and the map use the geography and subject slicers below.')
year = st.sidebar.selectbox('Academic year (single-year charts)', all_years, index=len(all_years)-1)
subjects = st.sidebar.multiselect('Creative-related subject groups', list(SUBJECTS.values()), default=list(SUBJECTS.values()))

countries = sorted(locations['Country'].dropna().unique().tolist())
country = st.sidebar.selectbox('Country', ['All countries', *countries])
geo = locations.copy()
if country != 'All countries':
    geo = geo[geo['Country'].eq(country)]
regions = sorted(geo['Region'].dropna().unique().tolist())
region = st.sidebar.selectbox('Region', ['All regions', *regions])
if region != 'All regions':
    geo = geo[geo['Region'].eq(region)]

ocn_las = get_ocn_local_authorities()
area = st.sidebar.selectbox('Distinct area', ['All areas', 'One Creative North', 'South Central'])
if area == 'South Central':
    geo = geo[geo['Local_Authority'].astype('string').str.strip().str.casefold().isin({s.casefold() for s in SOUTH_CENTRAL})]
elif area == 'One Creative North':
    if ocn_las:
        geo = geo[geo['Local_Authority'].astype('string').str.strip().str.casefold().isin(ocn_las)]
    else:
        # Clear regional proxy, never falsely claim exact OCN membership.
        geo = geo[geo['Region'].isin(NORTHERN_REGIONS)]
        st.sidebar.warning('Exact One Creative North LA list not found in config.py. Using North East, North West and Yorkshire & Humber as a provisional regional proxy.')

local_options = sorted(geo['Local_Authority'].dropna().unique().tolist())
local_authorities = st.sidebar.multiselect('Local Authority', local_options)
if local_authorities:
    geo = geo[geo['Local_Authority'].isin(local_authorities)]

if country != 'All countries' or region != 'All regions' or area != 'All areas' or local_authorities:
    st.caption('Geography filter active: providers without a verified Region/Local Authority may be omitted from comparisons.')

# Provider filter follows selected geography and subjects across all years.
visible_provider_ids = set(geo['UKPRN'].dropna())
subject_df = df[df['Subject_label'].isin(subjects) & df['UKPRN'].isin(visible_provider_ids)].copy()
provider_options = sorted(subject_df['Provider'].dropna().unique().tolist())
providers = st.sidebar.multiselect('University / provider (optional)', provider_options)
if providers:
    subject_df = subject_df[subject_df['Provider'].isin(providers)]

selected_ids = set(subject_df['UKPRN'].dropna())
geo = geo[geo['UKPRN'].isin(selected_ids)].copy()
this_year = subject_df[subject_df['Academic_year'].eq(year)].copy()
summary = make_summary(this_year, ['UKPRN', 'Provider', 'Subject_label'])
if summary.empty:
    st.warning('No graduate records for the selected year and filters. Try a different year, subject or geography.')
    st.stop()

by_provider = summary.groupby(['UKPRN', 'Provider'], as_index=False)[['Graduates', 'Respondents', 'Employed']].sum()
by_provider['Employment_pct_respondents'] = 100 * by_provider['Employed'].div(by_provider['Respondents'].replace(0, float('nan')))
summary_geo = by_provider.merge(geo.drop(columns=['Provider'], errors='ignore'), on='UKPRN', how='left')
grad = summary['Graduates'].sum(); respondents = summary['Respondents'].sum(); employed = summary['Employed'].sum()
a, b, c, d = st.columns(4)
a.metric('Graduates', f'{grad:,.0f}')
b.metric('Respondents (known outcomes)', f'{respondents:,.0f}')
c.metric('Employed', f'{employed:,.0f}')
d.metric('Employed / respondents', f'{employed / respondents * 100:.1f}%' if respondents else 'N/A')
st.caption(f'{len(by_provider):,} providers with outcomes in {year}. Figures are rounded by HESA; percentages are approximate.')

st.subheader('University / provider map')
show_all = st.toggle('Include selected providers without outcomes in the selected year', value=True)
metric = st.selectbox('Map indicator', ['Graduates', 'Respondents', 'Employed', 'Employed (% of respondents)'])
if show_all:
    mapdata = geo.merge(by_provider.drop(columns=['Provider']), on='UKPRN', how='left')
else:
    mapdata = summary_geo.copy()
mapdata['Provider'] = mapdata['Provider'].fillna('Unnamed provider')
for c in ['Graduates', 'Respondents', 'Employed']:
    mapdata[c] = pd.to_numeric(mapdata[c], errors='coerce').fillna(0)
mapdata['Employment_pct_respondents'] = 100 * mapdata['Employed'].div(mapdata['Respondents'].replace(0, float('nan')))
mapdata = mapdata.dropna(subset=['Latitude', 'Longitude'])
if mapdata.empty:
    st.info('No map points available for these filters.')
else:
    hover = {'City': True, 'Region': True, 'Local_Authority': True, 'Graduates': ':,.0f',
             'Respondents': ':,.0f', 'Employed': ':,.0f', 'Employment_pct_respondents': ':.1f',
             'Latitude': False, 'Longitude': False}
    hover = {k:v for k,v in hover.items() if k in mapdata.columns}
    if metric == 'Employed (% of respondents)':
        fig = px.scatter_map(mapdata, lat='Latitude', lon='Longitude', color='Employment_pct_respondents',
                             color_continuous_scale='Viridis', range_color=(0,100), hover_name='Provider',
                             hover_data=hover, map_style='open-street-map', zoom=4.4, center={'lat':54.6,'lon':-3.2})
        fig.update_traces(marker={'size': 11})
    else:
        mapdata['_size'] = mapdata[metric] + 1
        fig = px.scatter_map(mapdata, lat='Latitude', lon='Longitude', size='_size', size_max=29,
                             hover_name='Provider', hover_data=hover, map_style='open-street-map',
                             zoom=4.4, center={'lat':54.6,'lon':-3.2})
    fig.update_layout(height=540, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f'{mapdata.UKPRN.nunique():,} provider pins; approximate city/town-centre locations, not campuses. Multiple providers may share coordinates.')

st.subheader('Geographic comparisons')
geo_metric = st.selectbox('Measure for geographic charts', ['Graduates', 'Respondents', 'Employed', 'Employment_pct_respondents'],
                          format_func=lambda x: 'Employed (% of respondents)' if x == 'Employment_pct_respondents' else x)
left, right = st.columns(2)
with left:
    st.markdown('**By region**')
    reg = summary_geo.dropna(subset=['Region']).groupby('Region', as_index=False)[['Graduates','Respondents','Employed']].sum()
    reg['Employment_pct_respondents'] = 100 * reg['Employed'].div(reg['Respondents'].replace(0,float('nan')))
    if reg.empty:
        st.info('No classified regions in this selection.')
    else:
        reg = reg.sort_values(geo_metric)
        st.plotly_chart(px.bar(reg,x=geo_metric,y='Region',orientation='h',hover_data=['Graduates','Respondents','Employed'],
                               labels={'Region':'','Employment_pct_respondents':'Employed (%)'}), use_container_width=True)
with right:
    st.markdown('**By Local Authority**')
    las = summary_geo.dropna(subset=['Local_Authority']).groupby(['Region','Local_Authority'],dropna=False,as_index=False)[['Graduates','Respondents','Employed']].sum()
    las['Employment_pct_respondents'] = 100 * las['Employed'].div(las['Respondents'].replace(0,float('nan')))
    top_n = st.slider('Top Local Authorities', min_value=5, max_value=40, value=15, step=5)
    if las.empty:
        st.info('No Local Authority classification for this selection.')
    else:
        view = las.nlargest(top_n, geo_metric).sort_values(geo_metric)
        st.plotly_chart(px.bar(view,x=geo_metric,y='Local_Authority',orientation='h',
                               hover_data=['Region','Graduates','Respondents','Employed'],
                               labels={'Local_Authority':'','Employment_pct_respondents':'Employed (%)'}),use_container_width=True)
st.caption('The above charts group graduates by provider location, not workplace. Missing Local Authority assignments are excluded; London providers without verified boroughs are grouped as “London (borough not specified)”.')

st.subheader('Graduates, respondents and employed — selected year')
subj = summary.groupby('Subject_label', as_index=False)[['Graduates','Respondents','Employed']].sum()
long_subj = subj.melt('Subject_label',value_vars=['Graduates','Respondents','Employed'],var_name='Measure',value_name='People')
st.plotly_chart(px.bar(long_subj,x='Subject_label',y='People',color='Measure',barmode='group',
                       labels={'Subject_label':'Subject','People':'People'}),use_container_width=True)

st.subheader('Employment trends across academic years')
st.caption('All years, with the same country, region, distinct area, Local Authority, subject and provider filters. The single-year selector affects the map and comparison charts above.')
trend = make_summary(subject_df, ['Academic_year'])
trend = trend.sort_values('Academic_year')
col1,col2 = st.columns(2)
with col1:
    st.markdown('**Graduates, respondents and employed graduates by year**')
    long_trend = trend.melt('Academic_year',value_vars=['Graduates','Respondents','Employed'],var_name='Measure',value_name='People')
    st.plotly_chart(px.line(long_trend,x='Academic_year',y='People',color='Measure',markers=True,
                            labels={'Academic_year':'Academic year','People':'People'}),use_container_width=True)
with col2:
    st.markdown('**Employment as % of respondents**')
    fig_rate=px.line(trend,x='Academic_year',y='Employment_pct_respondents',markers=True,
                     labels={'Academic_year':'Academic year','Employment_pct_respondents':'Employed (% of respondents)'})
    fig_rate.update_layout(yaxis_range=[0,100])
    st.plotly_chart(fig_rate,use_container_width=True)

with st.expander('Annual employment figures / download'):
    cols=['Academic_year','Graduates','Respondents','Employed','Employment_pct_respondents']
    st.dataframe(trend[cols],hide_index=True,use_container_width=True)
    st.download_button('Download annual trends', trend[cols].to_csv(index=False).encode(),
                       file_name='creative_education_employment_trends.csv',mime='text/csv')

st.subheader('Universities / providers')
provider_rows=summary_geo[['Provider','City','Region','Local_Authority','Graduates','Respondents','Employed','Employment_pct_respondents']].sort_values('Graduates',ascending=False)
st.dataframe(provider_rows,hide_index=True,use_container_width=True)
st.download_button('Download selected provider outcomes',provider_rows.to_csv(index=False).encode(),
                   file_name='creative_education_provider_results.csv',mime='text/csv')

with st.expander('Definitions and caveats'):
    st.markdown('''- **Graduates**: HESA published total in selected subject groups. **Respondents**: graduates with known outcomes. **Employed**: full-time, part-time, unknown pattern, or employment alongside further study. The categories are not added twice.
- **Employed (% of respondents)** = employed / respondents × 100, not employed / all graduates.
- Uses HESA Table 28: all qualifications, all study modes, and the exclusion of significant interim study. Values are rounded.
- The **distinct area** selector filters providers located within the selected area, not graduates residing or working there. South Central uses the Atlas's supplied geography, including the combined Bournemouth, Christchurch and Poole authority.
- If `OCN_ALL` is available in `config.py`, One Creative North uses those Local Authorities. Otherwise it uses a *provisional northern-region proxy* with an explicit warning.
- Only providers with assigned regions or authorities appear in those corresponding slicers/charts. No inferred London boroughs.
- Geographic points are approximate reference city centres and must not be interpreted as exact campus locations. Employment outcomes do **not** establish talent retention.''')
