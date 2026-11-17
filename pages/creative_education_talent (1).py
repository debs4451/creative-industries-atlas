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
locpath=locate('university_locations.csv')
if locpath:
    locations=pd.read_csv(locpath,dtype={'UKPRN':'string'})
    locations['UKPRN']=locations['UKPRN'].str.replace(r'\.0$','',regex=True)
    locations=locations.rename(columns={'latitude':'Latitude','longitude':'Longitude','lat':'Latitude','lon':'Longitude'})
    if not {'Latitude','Longitude'}.issubset(locations.columns):
        st.error('Locations CSV needs UKPRN, Latitude, Longitude columns.')
    else:
        p=pivot.groupby(['UKPRN','Provider'],as_index=False).agg(Graduates=('Total','sum'),Known=('Known','sum'),Employed=('Employed','sum'))
        locations=locations.drop_duplicates('UKPRN')
        geo=p.merge(locations.drop(columns=['Provider'], errors='ignore'),on='UKPRN',how='left')
        geo['Latitude']=pd.to_numeric(geo.Latitude,errors='coerce')
        geo['Longitude']=pd.to_numeric(geo.Longitude,errors='coerce')
        mapped=geo.dropna(subset=['Latitude','Longitude']).copy()
        if mapped.empty:
            st.warning('No matching coordinates found. Check university_locations.csv UKPRNs.')
        else:
            fig=px.scatter_map(mapped,lat='Latitude',lon='Longitude',size='Graduates',hover_name='Provider',hover_data={'Graduates':':,.0f','UKPRN':True,'Latitude':False,'Longitude':False},zoom=4.5,center={'lat':54.6,'lon':-3.2},map_style='open-street-map',size_max=32)
            fig.update_layout(height=570,margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig,use_container_width=True)
            st.caption(f'Mapped {mapped.UKPRN.nunique()} of {geo.UKPRN.nunique()} providers with coordinate matches. Pins mark provider reference locations (not necessarily the teaching campus).')
else:
    st.warning('University map needs data/university_locations.csv (UKPRN, Latitude, Longitude). See the included location-building script to generate a first-pass file.')

left,right=st.columns(2)
with left:
    st.subheader('Graduates by subject')
    bysubject=pivot.groupby('Subject_label',as_index=False)['Total'].sum().sort_values('Total',ascending=False)
    st.plotly_chart(px.bar(bysubject,x='Total',y='Subject_label',orientation='h',labels={'Total':'Graduates','Subject_label':''}),use_container_width=True)
with right:
    st.subheader('Institutions with most graduates')
    byprovider=pivot.groupby('Provider',as_index=False)['Total'].sum().nlargest(15,'Total').sort_values('Total')
    st.plotly_chart(px.bar(byprovider,x='Total',y='Provider',orientation='h',labels={'Total':'Graduates','Provider':''}),use_container_width=True)

st.subheader('Trends across academic years')
trend=df[df.Subject_label.isin(subjects)]
if chosen:trend=trend[trend.Provider.isin(chosen)]
trend=trend[trend.Activity=='Total'].groupby(['Academic_year','Subject_label'],as_index=False)['Number'].sum()
if not trend.empty:
    st.plotly_chart(px.line(trend,x='Academic_year',y='Number',color='Subject_label',markers=True,labels={'Academic_year':'Academic year','Number':'Graduates','Subject_label':'Subject'}),use_container_width=True)

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
- If a provider has multiple campuses, the provider pin does not establish the campus where a graduate studied.''')
