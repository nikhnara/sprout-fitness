"""Rebuild provenance-preserving nutrition library from official USDA SR Legacy CSV archive."""
import csv, io, json, sys, zipfile, hashlib
from pathlib import Path
z=zipfile.ZipFile(sys.argv[1])
def rows(file):
 name=next(n for n in z.namelist() if n.endswith('/'+file))
 return csv.DictReader(io.TextIOWrapper(z.open(name)))
categories={r['id']:r['description'] for r in rows('food_category.csv')}
foods={r['fdc_id']:{'id':r['fdc_id'],'name':r['description'],'category':categories.get(r['food_category_id'],'Other'),'categoryId':r['food_category_id'],'source':'USDA SR Legacy (April 2018)','sourceUrl':f"https://fdc.nal.usda.gov/food-details/{r['fdc_id']}/nutrients",'basisGrams':100,'nutrients':{},'portions':[]} for r in rows('food.csv')}
keys={'1008':'kcal','1003':'protein','1004':'fat','1005':'carbs','1079':'fiber'}
for r in rows('food_nutrient.csv'):
 if r['fdc_id'] in foods and r['nutrient_id'] in keys:
  foods[r['fdc_id']]['nutrients'][keys[r['nutrient_id']]]=float(r['amount']) if r['amount'] else None
for r in rows('food_portion.csv'):
 if r['fdc_id'] in foods and float(r['gram_weight'] or 0)>0:
  label=' '.join(filter(None,[r['amount'],r['modifier'],r['portion_description']])).strip()
  foods[r['fdc_id']]['portions'].append({'label':label,'grams':float(r['gram_weight'])})
# Diet filters are conservative catalog tags, not ingredient certification.
plant={'2','9','11','12','16','20'}
for f in foods.values():
 cat=f['categoryId']; name=f['name'].lower()
 f['diet']='plant' if cat in plant else 'dairy' if cat=='1' and not any(w in name for w in ['egg','baby','infant']) else 'other'
 if any(w in name for w in ['beef','pork','chicken','turkey','fish','anchov','bacon','lard','gelatin','shrimp','clam','oyster','sausage','ham,','meat','veal','lamb','duck']): f['diet']='other'
 f['nutrients']={k:f['nutrients'].get(k) for k in keys.values()}
 f['portions']=f['portions'][:8]
ordered=sorted(foods.values(),key=lambda f:(not any(s in f['name'].lower() for s in ['lentils, mature seeds, cooked','chickpeas (garbanzo beans, bengal gram), mature seeds, cooked','yogurt, greek, plain, nonfat','tofu, raw, firm','oats','bananas, raw','rice, white, long-grain, regular, enriched, cooked']),f['name']))
root=Path(__file__).resolve().parents[1]
(root/'dist/foods.json').write_text(json.dumps(ordered,separators=(',',':')))
(root/'dist/data-provenance.json').write_text(json.dumps({'source':'USDA FoodData Central SR Legacy','release':'April 2018','download':'https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip','sha256':hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),'records':len(ordered),'basis':'per 100 g edible portion','missingNutrients':'null, never assumed zero','dietClassification':'Category and keyword heuristic; inspect ingredients for strict dietary requirements.','indianData':'IFCT reference identified; not yet imported or represented as verified IFCT values.'},indent=2))
print('Imported',len(ordered),'foods')
