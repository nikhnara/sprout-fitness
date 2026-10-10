import {restaurantFoods,restaurantName} from '../dist/restaurants.mjs';
import fs from 'node:fs';
import {personalCatalog} from '../dist/personal.mjs';
const base=JSON.parse(fs.readFileSync('dist/foods.json','utf8')),p=personalCatalog(base);
const all=[...p.favorites,...p.extras,...restaurantFoods,...base],seen=new Set();
const foods=all.filter(f=>f.id&&!seen.has(f.id)&&seen.add(f.id));
const sources=new Map(),rows=[];
for(const f of foods){
 if(!f.name?.trim()||!f.nutrients||f.basisGrams!==100)throw Error('Invalid food '+f.id);
 if(restaurantName(f))f.restaurant=restaurantName(f);
 const sourceId=f.source?.startsWith('USDA')?'usda-sr-2018':f.estimated?'gamna-recipe-v1':'label-'+f.id;
 sources.set(sourceId,{source_id:sourceId,name:f.source||'Recipe calculation',url:f.sourceUrl||null,release_date:sourceId==='usda-sr-2018'?'2018-04-01':null});
 rows.push({food_id:String(f.id),source_id:sourceId,name:f.displayName||f.name,canonical_name:f.name,diet:f.diet||'other',category:f.category||null,basis_grams:100,estimated:!!f.estimated,record:f});
}
fs.writeFileSync('data/catalog.ndjson',rows.map(JSON.stringify).join('\n')+'\n');
fs.writeFileSync('data/sources.ndjson',[...sources.values()].map(JSON.stringify).join('\n')+'\n');
console.log(`${rows.length} foods, ${sources.size} sources exported with stable identifiers`);
