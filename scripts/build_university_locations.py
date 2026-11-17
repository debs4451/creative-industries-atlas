"""OPTIONAL one-time approximate provider geocoding helper.
Install: pip install pandas geopy
Run: python build_university_locations.py creative_graduate_outcomes_with_computing.csv
Uses Nominatim with 1.1-second interval; please respect its usage policy and review matches.
Prefer an authoritative provider/campus address reference rather than geocoding names.
"""
import sys
from pathlib import Path
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
src=Path(sys.argv[1]) if len(sys.argv)>1 else Path('creative_graduate_outcomes_with_computing.csv')
df=pd.read_csv(src,dtype={'UKPRN':'string'})
providers=df[['UKPRN','Provider']].dropna().drop_duplicates('UKPRN').copy()
providers=providers[providers.Provider.ne('Total')]
out=src.with_name('university_locations.csv')
if out.exists():
    prev=pd.read_csv(out,dtype={'UKPRN':'string'})
    providers=providers.merge(prev[['UKPRN','Latitude','Longitude']],on='UKPRN',how='left')
else:
    providers['Latitude']=float('nan');providers['Longitude']=float('nan')
geocoder=Nominatim(user_agent='creative-industries-atlas-provider-geocode-v1')
geocode=RateLimiter(geocoder.geocode,min_delay_seconds=1.1,max_retries=1,swallow_exceptions=True)
for idx,row in providers.iterrows():
    if pd.notna(row.Latitude) and pd.notna(row.Longitude):continue
    query=f'{row.Provider}, United Kingdom'
    match=geocode(query, exactly_one=True, country_codes='gb')
    if match:
        providers.loc[idx,'Latitude']=match.latitude;providers.loc[idx,'Longitude']=match.longitude
    providers.to_csv(out,index=False)
    print(f'{row.Provider}: {"matched" if match else "not found"}')
print('Saved:',out,'— manually validate coordinates before publishing.')
