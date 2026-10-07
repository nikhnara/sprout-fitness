"""Validate the public JSON boundary before accepting personal health records."""
import datetime, json, math, re

def number(v, low, high, optional=False):
    if optional and v is None: return
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not low <= v <= high:
        raise ValueError('A numeric field is missing or outside its allowed range.')

def validate_state(s):
    if not isinstance(s, dict) or s.get('version') != 1: raise ValueError('Unsupported diary format.')
    if len(json.dumps(s, allow_nan=False).encode()) > 800_000: raise ValueError('Diary exceeds the 800 KB snapshot limit. Export and archive older records before syncing.')
    if not isinstance(s.get('days'), dict) or len(s['days']) > 3660: raise ValueError('Invalid diary days.')
    p=s.get('profile', {})
    if not isinstance(p.get('name'), str) or not 1 <= len(p['name']) <= 60: raise ValueError('Invalid profile name.')
    for k, maxv in {'kcal':10000,'protein':1000,'carbs':1000,'fat':1000,'fiber':1000,'sleep':24,'exercise':1440}.items(): number(p.get('targets',{}).get(k),1,maxv)
    for date,d in s['days'].items():
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date): raise ValueError('Invalid date.')
        datetime.date.fromisoformat(date)
        number(d.get('weight'),20,400,True); number(d.get('sleep'),0,24,True)
        if not isinstance(d.get('meals'),list) or len(d['meals']) > 200: raise ValueError('Invalid meal list.')
        for m in d['meals']:
            number(m.get('grams'),.1,10000)
            if not isinstance(m.get('name'),str) or len(m['name']) > 500: raise ValueError('Invalid food name.')
            for k in ['kcal','protein','fat','carbs','fiber']: number(m.get('nutrients',{}).get(k),0,100000,True)
        if not isinstance(d.get('exercise'),list) or len(d['exercise']) > 100: raise ValueError('Invalid activity list.')
        for e in d['exercise']: number(e.get('minutes'),1,1440)
    for key in ['customFoods','recipes']:
        if not isinstance(s.get(key),list) or len(s[key]) > 2000: raise ValueError('Invalid custom food list.')
    return s
