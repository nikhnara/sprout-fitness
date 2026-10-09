"""Validate the public JSON boundary before accepting personal health records."""
import datetime, json, math, re
from urllib.parse import urlparse

def number(v, low, high, optional=False):
    if optional and v is None: return
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not low <= v <= high:
        raise ValueError('A numeric field is missing or outside its allowed range.')

def validate_state(s):
    if not isinstance(s, dict) or s.get('version') != 1: raise ValueError('Unsupported diary format.')
    if len(json.dumps(s, allow_nan=False).encode()) > 800_000: raise ValueError('Diary exceeds the 800 KB snapshot limit. Export and archive older records before syncing.')
    if not isinstance(s.get('days'), dict) or len(s['days']) > 3660: raise ValueError('Invalid diary days.')
    p=s.get('profile', {})
    if not isinstance(p,dict) or not isinstance(p.get('targets'),dict): raise ValueError('Invalid profile.')
    if not isinstance(p.get('name'), str) or not 1 <= len(p['name']) <= 60: raise ValueError('Invalid profile name.')
    if set(p['targets']) != {'kcal','protein','carbs','fat','fiber','sleep','exercise'}: raise ValueError('Invalid goal fields.')
    for k, maxv in {'kcal':10000,'protein':1000,'carbs':1000,'fat':1000,'fiber':1000,'sleep':24,'exercise':1440}.items(): number(p.get('targets',{}).get(k),1,maxv)
    for date,d in s['days'].items():
        if not isinstance(d,dict): raise ValueError('Invalid diary day.')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date): raise ValueError('Invalid date.')
        datetime.date.fromisoformat(date)
        number(d.get('weight'),20,400,True); number(d.get('sleep'),0,24,True)
        if not isinstance(d.get('meals'),list) or len(d['meals']) > 200: raise ValueError('Invalid meal list.')
        for m in d['meals']:
            if not isinstance(m,dict) or not isinstance(m.get('nutrients'),dict): raise ValueError('Invalid meal.')
            if 'food' in m: validate_food(m['food'])
            number(m.get('grams'),.1,10000)
            if not isinstance(m.get('name'),str) or len(m['name']) > 500: raise ValueError('Invalid food name.')
            for k in ['kcal','protein','fat','carbs','fiber']: number(m.get('nutrients',{}).get(k),0,100000,True)
        if not isinstance(d.get('exercise'),list) or len(d['exercise']) > 100: raise ValueError('Invalid activity list.')
        for e in d['exercise']:
            if not isinstance(e,dict): raise ValueError('Invalid activity.')
            number(e.get('minutes'),1,1440)
    for key in ['customFoods','recipes']:
        if not isinstance(s.get(key),list) or len(s[key]) > 2000: raise ValueError('Invalid custom food list.')
        for food in s[key]: validate_food(food)
    validate_tree(s)
    return s


def validate_tree(value,depth=0):
    if depth>18: raise ValueError('Diary nesting is too deep.')
    if isinstance(value,dict):
        if any(not isinstance(k,str) or len(k)>100 for k in value): raise ValueError('Invalid field name.')
        for k,v in value.items():
            if k in ('sourceUrl','url') and v and (not isinstance(v,str) or not v.startswith('https://')): raise ValueError('Links must use HTTPS.')
            if k=='image' and v:
                if not isinstance(v,str) or not ((v.startswith('assets/') and '..' not in v) or (urlparse(v).scheme=='https' and urlparse(v).hostname=='images.openfoodfacts.org')): raise ValueError('Invalid food image.')
            validate_tree(v,depth+1)
    elif isinstance(value,list):
        if len(value)>4000: raise ValueError('Too many items.')
        for v in value: validate_tree(v,depth+1)
    elif isinstance(value,str) and len(value)>2000: raise ValueError('Text is too long.')


def validate_activity(data):
    if not isinstance(data,dict) or set(data)-{'date','sourceId','name','minutes','sleep','weight'}: raise ValueError('Invalid fields.')
    if not isinstance(data.get('sourceId'),str) or not 1<=len(data['sourceId'])<=120: raise ValueError('Invalid source ID.')
    datetime.date.fromisoformat(data.get('date',''))
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',data['date']): raise ValueError('Invalid date.')
    if not any(k in data for k in ('minutes','sleep','weight')): raise ValueError('No measurements.')
    for key,low,high in [('minutes',1,1440),('sleep',0,24),('weight',20,400)]:
        if key in data: number(data[key],low,high)
    if 'minutes' in data and (not isinstance(data.get('name'),str) or not 1<=len(data['name'])<=100): raise ValueError('Name required.')
    return data


def validate_food(food,depth=0):
    if depth>8 or not isinstance(food,dict): raise ValueError('Invalid food record.')
    for key in ['id','name']:
        if not isinstance(food.get(key),str) or not 1<=len(food[key])<=500: raise ValueError('Invalid food identity.')
    nutrients=food.get('nutrients')
    if not isinstance(nutrients,dict): raise ValueError('Invalid nutrition.')
    for key in ['kcal','protein','fat','carbs','fiber']:number(nutrients.get(key),0,100000,True)
    for key in ['defaultGrams','batchGrams','basisGrams']:
        if key in food:number(food[key],.1,20000)
    portions=food.get('portions',[])
    if not isinstance(portions,list) or len(portions)>100:raise ValueError('Invalid portions.')
    for portion in portions:
        if not isinstance(portion,dict) or not isinstance(portion.get('label'),str):raise ValueError('Invalid portion.')
        number(portion.get('grams'),.1,20000)
    if 'ingredients' in food:
        if not isinstance(food['ingredients'],list) or len(food['ingredients'])>200:raise ValueError('Invalid recipe.')
        for ingredient in food['ingredients']:
            if not isinstance(ingredient,dict):raise ValueError('Invalid ingredient.')
            number(ingredient.get('grams'),.1,10000)
            validate_food(ingredient.get('food'),depth+1)
