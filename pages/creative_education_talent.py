"""Creative Education & Graduate Outcomes — Streamlit page for Creative Industries Atlas.
Place in pages/creative_education_talent.py and CSV in data/ (or repository root).
Optional: data/university_locations.csv columns UKPRN,Latitude,Longitude (plus optional City,Region).
Do not interpret graduate employment as regional talent retention.
"""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Creative Education & Talent', page_icon='🎓', layout='wide')
BASE=Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name=='pages' else Path(__file__).resolve().parent
DATA_NAME='creative_graduate_outcomes_with_computing.csv'
SUBJECT_NAMES={
    '11 Computing':'Computing',
    '13 Architecture, building and planning':'Architecture, building & planning',
    '24 Media, journalism and communications':'Media, journalism & communications',
    '25 Design, and creative and performing arts':'Design, creative & performing arts',
}

def locate(name):
    for path in (BASE/'data'/name, BASE/name, BASE/'assets'/name):
        if path.exists():return path
    return None

@st.cache_data(show_spinner=False)
def load_data(filepath):
    df=pd.read_csv(filepath,dtype={'UKPRN':'string'},low_memory=False)
    df['UKPRN']=df['UKPRN'].astype('string').str.replace(r'\.0$','',regex=True)
    df['Number']=pd.to_numeric(df['Number'],errors='coerce').fillna(0)
    df['Subject_label']=df['Subject'].map(SUBJECT_NAMES)
    df=df[df['Subject_label'].notna() & df['Provider'].ne('Total') & df['UKPRN'].notna()].copy()
    return df

st.title('🎓 Creative Education & Graduate Outcomes')
st.caption('Source: HESA Graduate Outcomes, Table 28 | Academic years 2017/18–2023/24')
st.info('This page maps the **institution where someone studied**, not where they subsequently work. Employment outcomes are not the same as local talent retention. Computing and Architecture are broad subject groups that also include non-creative courses.')
path=locate(DATA_NAME)
if path is None:
    st.error(f'Cannot find {DATA_NAME}. Add it to your data/ folder or repository root.')
    st.stop()
df=load_data(str(path))
years=sorted(df.Academic_year.dropna().unique().tolist())
year=st.selectbox('Academic year',years,index=len(years)-1)
subjects=st.multiselect('Subject groups',list(SUBJECT_NAMES.values()),default=list(SUBJECT_NAMES.values()))
filtered=df[(df.Academic_year==year)&df.Subject_label.isin(subjects)]
providers=sorted(filtered.Provider.dropna().unique().tolist())
chosen=st.multiselect('Universities / higher education providers (optional)',providers)
if chosen: filtered=filtered[filtered.Provider.isin(chosen)]
if filtered.empty:
    st.warning('No records for this selection.')
    st.stop()

# Each activity is exclusive. Do NOT sum published Total with activity sub-categories.
pivot=filtered.pivot_table(index=['UKPRN','Provider','Subject_label'],columns='Activity',values='Number',aggfunc='sum',fill_value=0).reset_index()
for col in ['Total','Total with known outcomes','Full-time employment','Part-time employment','Unknown pattern of employment','Employment and further study','Non-respondents','Unemployed']:
    if col not in pivot:pivot[col]=0
pivot['Employed']=pivot['Full-time employment']+pivot['Part-time employment']+pivot['Unknown pattern of employment']+pivot['Employment and further study']
pivot['Known']=pivot['Total with known outcomes']
pivot['Employment_pct_known']=pivot['Employed'].div(pivot['Known'].replace(0,float('nan')))*100
pivot['Response_pct']=pivot['Known'].div(pivot['Total'].replace(0,float('nan')))*100

# Caution: HESA rounds individual counts. Counts/rates calculated from them are approximate.
total_grad=pivot['Total'].sum(); known=pivot['Known'].sum(); employed=pivot['Employed'].sum()
a,b,c,d=st.columns(4)
a.metric('Creative-related graduates',f'{total_grad:,.0f}')
b.metric('Providers',f'{pivot.UKPRN.nunique():,}')
c.metric('Employed among known outcomes',f'{100*employed/known:.1f}%' if known else 'N/A')
d.metric('Known-outcome response',f'{100*known/total_grad:.1f}%' if total_grad else 'N/A')
st.caption('Broad subject groups, not an estimate of creative-sector jobs. Percentages use respondents with known outcomes; published HESA counts are rounded.')

st.subheader('Map of university locations')
st.caption('Dots show approximate provider reference city/town centres, not verified campus or teaching locations. Several providers may share a pin.')
locpath=locate('university_locations.csv')
if locpath:
    locations=pd.read_csv(locpath,dtype={'UKPRN':'string'})
    locations['UKPRN']=locations['UKPRN'].str.replace(r'\.0$','',regex=True)
    locations=locations.rename(columns={'latitude':'Latitude','longitude':'Longitude','lat':'Latitude','lon':'Longitude'})
    if not {'Latitude','Longitude'}.issubset(locations.columns):
        st.error('Locations CSV needs UKPRN, Latitude and Longitude columns.')
    else:
        p=pivot.groupby(['UKPRN','Provider'],as_index=False).agg(
            Graduates=('Total','sum'), Known=('Known','sum'), Employed=('Employed','sum'))
        p['Employment_pct_respondents'] = 100*p['Employed'].div(p['Known'].replace(0,float('nan')))
        locations=locations.drop_duplicates('UKPRN')
        show_all=st.toggle('Show all 405 providers, including those without graduate outcomes in the selected year',value=True)
        map_metric=st.selectbox(
            'Map indicator',
            ['Graduates', 'Employed graduates', 'Employed (% of respondents)'],
            help='The percentage is employed graduates divided by graduates with known outcomes (respondents), not all graduates.'
        )
        if show_all:
            mapped=locations.copy()
            mapped=mapped.merge(
                p.drop(columns=['Provider']),on='UKPRN',how='left')
            mapped['Provider']=mapped['Provider'].fillna('Unnamed provider')
        else:
            mapped=p.merge(locations.drop(columns=['Provider'],errors='ignore'),on='UKPRN',how='left')
        for numeric_col in ['Graduates','Employed','Known']:
            mapped[numeric_col]=pd.to_numeric(mapped[numeric_col],errors='coerce').fillna(0)
        mapped['Employment_pct_respondents']=100*mapped['Employed'].div(mapped['Known'].replace(0,float('nan')))
        if map_metric=='Graduates':
            metric_col='Graduates'
        elif map_metric=='Employed graduates':
            metric_col='Employed'
        else:
            metric_col='Employment_pct_respondents'
        mapped['Latitude']=pd.to_numeric(mapped.Latitude,errors='coerce')
        mapped['Longitude']=pd.to_numeric(mapped.Longitude,errors='coerce')
        mapped=mapped.dropna(subset=['Latitude','Longitude']).copy()
        if mapped.empty:
            st.warning('No coordinates found for the selected providers.')
        else:
            hover={'UKPRN':True,'Latitude':False,'Longitude':False,
                   'Graduates':':,.0f','Employed':':,.0f',
                   'Known':':,.0f','Employment_pct_respondents':':.1f'}
            if 'City' in mapped.columns: hover['City']=True
            # Fixed-size markers for percentage, so a small provider with a high rate
            # is not visually mistaken for a large provider.
            if map_metric=='Employed (% of respondents)':
                fig=px.scatter_map(mapped,lat='Latitude',lon='Longitude',
                                   color='Employment_pct_respondents',
                                   color_continuous_scale='Viridis',range_color=(0,100),
                                   hover_name='Provider',hover_data=hover,
                                   zoom=4.5,center={'lat':54.6,'lon':-3.2},
                                   map_style='open-street-map')
                fig.update_traces(marker={'size':11,'opacity':0.85})
                fig.update_layout(coloraxis_colorbar_title='Employed (%)')
            else:
                mapped['_marker_size']=mapped[metric_col].clip(lower=0)+1
                fig=px.scatter_map(mapped,lat='Latitude',lon='Longitude',
                                   size='_marker_size',hover_name='Provider',
                                   hover_data=hover,zoom=4.5,
                                   center={'lat':54.6,'lon':-3.2},
                                   map_style='open-street-map',size_max=31)
            fig.update_layout(height=570,margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig,use_container_width=True)
            st.caption(f'Showing {mapped.UKPRN.nunique()} provider points. Percentage uses known-outcome respondents; providers without responses have no rate. City-centre pins are approximate and can overlap.')
else:
    st.warning('University map needs data/university_locations.csv (UKPRN, Latitude, Longitude).')

# Regional and Local Authority comparisons are based on the provider reference city
# in university_locations.csv, NOT on graduates' home/work locations or verified campuses.
st.subheader('Creative graduates by region and Local Authority')
st.caption(
    'These charts assign graduates to the approximate location of their higher education provider, '
    'not to where graduates live or work. They do not measure graduate retention. '
    'Providers without a known location are excluded from these charts.'
)
if not locpath:
    st.warning('Add data/university_locations.csv to enable the geographic charts.')
elif not {'Region', 'Local_Authority'}.issubset(locations.columns):
    st.warning('Update data/university_locations.csv to include Region and Local_Authority columns.')
else:
    geo_counts = p.merge(
        locations[['UKPRN', 'Region', 'Local_Authority']].drop_duplicates('UKPRN'),
        on='UKPRN', how='left'
    )
    region_counts = (
        geo_counts.dropna(subset=['Region'])
        .groupby('Region', as_index=False)
        .agg(Graduates=('Graduates', 'sum'), Providers=('UKPRN', 'nunique'))
        .sort_values('Graduates', ascending=True)
    )
    la_counts = (
        geo_counts.dropna(subset=['Region', 'Local_Authority'])
        .groupby(['Region', 'Local_Authority'], as_index=False)
        .agg(Graduates=('Graduates', 'sum'), Providers=('UKPRN', 'nunique'))
    )
    # London is a region comprising multiple boroughs. City-centre coordinates
    # cannot identify each provider's borough, so show a clearly labelled
    # London-wide aggregate rather than omitting London from the dropdown.
    london_unknown = geo_counts[
        geo_counts['Region'].eq('London') & geo_counts['Local_Authority'].isna()
    ]
    if not london_unknown.empty:
        london_row = pd.DataFrame([{
            'Region': 'London',
            'Local_Authority': 'London (borough not specified)',
            'Graduates': london_unknown['Graduates'].sum(),
            'Providers': london_unknown['UKPRN'].nunique(),
        }])
        la_counts = pd.concat([la_counts, london_row], ignore_index=True)
    left_geo, right_geo = st.columns(2)
    with left_geo:
        st.markdown('**Graduates by provider region**')
        if region_counts.empty:
            st.info('No providers have a mapped region.')
        else:
            fig_region = px.bar(
                region_counts, x='Graduates', y='Region', orientation='h',
                hover_data=['Providers'],
                labels={'Graduates': 'Graduates', 'Region': ''}
            )
            fig_region.update_layout(height=480, margin=dict(l=0,r=10,t=10,b=0))
            st.plotly_chart(fig_region, use_container_width=True)
    with right_geo:
        st.markdown('**Graduates by provider Local Authority**')
        region_options = ['All mapped regions'] + sorted(region_counts['Region'].dropna().unique().tolist())
        selected_region = st.selectbox('Filter Local Authorities by region', region_options)
        la_view = la_counts if selected_region == 'All mapped regions' else la_counts[la_counts['Region'] == selected_region]
        top_n = st.slider('Number of Local Authorities', min_value=5, max_value=30, value=15, step=5)
        if selected_region == 'London':
            st.caption('London is currently grouped at regional level: individual boroughs have not been verified.')
        la_view = la_view.nlargest(top_n, 'Graduates').sort_values('Graduates')
        if la_view.empty:
            st.info('No providers have a matched Local Authority in this selection.')
        else:
            fig_la = px.bar(
                la_view, x='Graduates', y='Local_Authority', orientation='h',
                hover_data=['Region', 'Providers'],
                labels={'Graduates': 'Graduates', 'Local_Authority': ''}
            )
            fig_la.update_layout(height=480, margin=dict(l=0,r=10,t=10,b=0))
            st.plotly_chart(fig_la, use_container_width=True)
    st.caption(
        f'Coverage: {geo_counts.dropna(subset=["Region"]).UKPRN.nunique()} of {p.UKPRN.nunique()} '
        f'selected providers have a region; '
        f'{geo_counts.dropna(subset=["Local_Authority"]).UKPRN.nunique()} have a Local Authority. '
        'London providers without verified boroughs are shown as London (borough not specified), not as an individual Local Authority. '
        'These administrative assignments are provisional and require provider-address verification.'
    )
    with st.expander('Download geography comparison tables'):
        st.download_button('Regional totals (CSV)', region_counts.to_csv(index=False).encode(),
                           file_name='creative_graduates_by_provider_region.csv', mime='text/csv')
        st.download_button('Local Authority totals (CSV)', la_counts.to_csv(index=False).encode(),
                           file_name='creative_graduates_by_provider_local_authority.csv', mime='text/csv')

left,right=st.columns(2)
with left:
    st.subheader('Graduates by subject')
    bysubject=pivot.groupby('Subject_label',as_index=False)['Total'].sum().sort_values('Total',ascending=False)
    st.plotly_chart(px.bar(bysubject,x='Total',y='Subject_label',orientation='h',labels={'Total':'Graduates','Subject_label':''}),use_container_width=True)
with right:
    st.subheader('Institutions with most graduates')
    byprovider=pivot.groupby('Provider',as_index=False)['Total'].sum().nlargest(15,'Total').sort_values('Total')
    st.plotly_chart(px.bar(byprovider,x='Total',y='Provider',orientation='h',labels={'Total':'Graduates','Provider':''}),use_container_width=True)

st.subheader('Graduates vs employed — selected academic year')
st.caption('Employed includes full-time, part-time, unknown work pattern, and employment with further study. Graduates includes non-respondents, so these bars measure different populations.')
comparison=(pivot.groupby('Subject_label',as_index=False)
            .agg(Graduates=('Total','sum'), Employed=('Employed','sum')))
if not comparison.empty:
    comparison_long=comparison.melt(id_vars='Subject_label',
                                    value_vars=['Graduates','Employed'],
                                    var_name='Measure',value_name='People')
    fig_comparison=px.bar(comparison_long,x='Subject_label',y='People',color='Measure',
                          barmode='group',labels={'Subject_label':'Subject group','People':'People'},
                          category_orders={'Subject_label':list(SUBJECT_NAMES.values())})
    fig_comparison.update_layout(xaxis_tickangle=-15,legend_title_text='',height=470)
    st.plotly_chart(fig_comparison,use_container_width=True)

st.subheader('Employment trends across academic years')
st.caption('All years use the same selected subjects and optional providers. The year selector above applies to the map and other single-year charts, not this historical comparison.')
trend_source=df[df.Subject_label.isin(subjects)]
if chosen:
    trend_source=trend_source[trend_source.Provider.isin(chosen)]
# Activity categories are mutually exclusive; do not add Total/Known to their components.
trend_activity=trend_source.groupby(['Academic_year','Activity'],as_index=False)['Number'].sum()
trend_wide=trend_activity.pivot(index='Academic_year',columns='Activity',values='Number').fillna(0)
for col in ['Total','Total with known outcomes','Full-time employment','Part-time employment',
            'Unknown pattern of employment','Employment and further study']:
    if col not in trend_wide.columns: trend_wide[col]=0
trend_wide['Graduates']=trend_wide['Total']
trend_wide['Respondents']=trend_wide['Total with known outcomes']
trend_wide['Employed']=(trend_wide['Full-time employment']+trend_wide['Part-time employment']+
                        trend_wide['Unknown pattern of employment']+trend_wide['Employment and further study'])
trend_wide['Employment_pct_respondents']=100*trend_wide['Employed'].div(trend_wide['Respondents'].replace(0,float('nan')))
trend_wide=trend_wide.reset_index().sort_values('Academic_year')
tr_left,tr_right=st.columns(2)
with tr_left:
    st.markdown('**Graduates and employed graduates by year**')
    long_trend=trend_wide.melt(id_vars='Academic_year',value_vars=['Graduates','Employed'],
                               var_name='Measure',value_name='People')
    fig_counts=px.line(long_trend,x='Academic_year',y='People',color='Measure',markers=True,
                       labels={'Academic_year':'Academic year','People':'Graduates / employed graduates'})
    fig_counts.update_layout(legend_title_text='',height=425)
    st.plotly_chart(fig_counts,use_container_width=True)
with tr_right:
    st.markdown('**Employment as a percentage of respondents**')
    fig_rate=px.line(trend_wide,x='Academic_year',y='Employment_pct_respondents',markers=True,
                     labels={'Academic_year':'Academic year','Employment_pct_respondents':'Employed (% of respondents)'})
    fig_rate.update_traces(hovertemplate='%{x}<extra></extra><br>Employed: %{y:.1f}%')
    fig_rate.update_layout(yaxis_range=[0,100],height=425)
    st.plotly_chart(fig_rate,use_container_width=True)
with st.expander('View / download annual employment figures'):
    st.dataframe(trend_wide[['Academic_year','Graduates','Respondents','Employed','Employment_pct_respondents']]
                 .rename(columns={'Academic_year':'Academic year',
                                  'Employment_pct_respondents':'Employed (% of respondents)'}),
                 hide_index=True,use_container_width=True)
    st.download_button('Download employment trends (CSV)',
                       trend_wide.to_csv(index=False).encode('utf-8'),
                       file_name='creative_graduate_employment_trends.csv',mime='text/csv')

st.subheader('Detailed provider and subject results')
cols=['Provider','Subject_label','Total','Known','Employed','Employment_pct_known','Response_pct']
st.dataframe(pivot[cols].rename(columns={'Subject_label':'Subject','Total':'Graduates','Known':'Known outcomes','Employment_pct_known':'Employment among known outcomes (%)','Response_pct':'Known-outcome response (%)'}).sort_values('Graduates',ascending=False),use_container_width=True,hide_index=True)
st.download_button('Download filtered provider results',data=pivot.to_csv(index=False).encode('utf-8'),file_name=f'creative_graduate_providers_{year.replace("/","-")}.csv',mime='text/csv')
with st.expander('Methodology and limitations'):
    st.markdown('''- HESA Table 28, academic years 2017/18–2023/24. Includes subject groups 11, 13, 24 and 25.
- Uses **All qualifications**, **All modes** and **Exclude significant interim study** to avoid counting overlapping subtotals.
- Creative classification is intentionally broad: Computing includes non-creative computing degrees; Architecture includes building and planning.
- Employment includes full-time, part-time, unknown pattern and employment with further study. Denominator is graduates with known outcomes.
- Figures are rounded by HESA; calculated sums and percentages are approximate.
- **Not a regional retention metric:** provider geography is not graduate workplace geography. Calculating retention requires matched study and workplace geography, ideally by subject and cohort.
- If a provider has multiple campuses, the provider pin does not establish the campus where a graduate studied.\n- The Region/Local Authority categories come from provisional provider-city assignments, not verified provider or campus locations; London boroughs are not inferred from a London-wide point. Geographic charts are limited to providers with assigned locations.''')
