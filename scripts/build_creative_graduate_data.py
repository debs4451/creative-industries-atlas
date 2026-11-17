"""Extract four broad creative-related HESA subject groups from Table 28 ZIP.
Run: python build_creative_graduate_data.py table-28.zip
"""
import csv, io, sys, zipfile
from pathlib import Path
import pandas as pd

SOURCE = Path(sys.argv[1]) if len(sys.argv)>1 else Path('table-28(2).zip')
OUT = Path(__file__).resolve().parent / 'creative_graduate_outcomes_with_computing.csv'
SUBJECT_PREFIXES = ('11 ', '13 ', '24 ', '25 ')
ACTIVITIES = ['Full-time employment','Part-time employment','Unknown pattern of employment','Voluntary or unpaid work','Employment and further study','Full-time further study','Part-time further study','Unknown pattern of further study','Other including travel, caring for someone or retired','Unemployed','Total with known outcomes','Non-respondents','Total']
rows = []
with zipfile.ZipFile(SOURCE) as archive:
    for filename in archive.namelist():
        if not filename.endswith('.csv'): continue
        with archive.open(filename) as raw:
            reader=csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8-sig'),restkey='extra')
            # metadata preamble: DictReader starts at Title; use raw csv rows instead
        with archive.open(filename) as raw:
            for r in csv.reader(io.TextIOWrapper(raw,encoding='utf-8-sig')):
                if len(r)!=9 or not (r[0].strip().isdigit() or r[0].strip()=='') or not r[2].startswith(SUBJECT_PREFIXES):continue
                ukprn,provider,subject,activity,interim,level,mode,year,number=r
                if interim!='Exclude significant interim study' or level!='All' or mode!='All':continue
                try: value=float(number.replace(',',''))
                except ValueError:continue
                rows.append([ukprn,provider,subject,activity.replace('\xa0',' '),year,value])
df=pd.DataFrame(rows,columns=['UKPRN','Provider','Subject','Activity','Academic_year','Number'])
df=df[df['Activity'].isin(ACTIVITIES)]
df.to_csv(OUT,index=False)
print(f'Saved {len(df):,} activity rows, {df.Provider.nunique()} providers, {df.Academic_year.nunique()} years to {OUT}')
