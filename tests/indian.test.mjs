import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {indianCatalog,recipeNutrition} from '../dist/indian.mjs';
import {scale} from '../dist/core.mjs';
const foods=JSON.parse(readFileSync(new URL('../dist/foods.json',import.meta.url)));
const catalog=indianCatalog(foods);
test('cooked yield changes density but preserves batch nutrition',()=>{
 const recipe=catalog.templates.find(f=>f.id==='template-chana');
 const a=recipeNutrition(recipe.ingredients,650),b=recipeNutrition(recipe.ingredients,1300);
 for(const k of Object.keys(a))assert.ok(Math.abs(a[k]-2*b[k])<1e-9);
 const fat=catalog.extras.find(f=>f.id==='172336');
 const changed=recipeNutrition([...recipe.ingredients,{food:fat,grams:5}],650);
 assert.ok(Math.abs((changed.kcal-a.kcal)*6.5-scale(fat.nutrients,5).kcal)<1e-9);
});
test('recipe unknowns and invalid amounts cannot silently become zeros',()=>{
 const paneer=catalog.extras.find(f=>f.id==='brand-amul-paneer');
 assert.equal(recipeNutrition([{food:paneer,grams:100}],200).fiber,null);
 for(const grams of [0,-1,NaN,Infinity,10001])assert.throws(()=>recipeNutrition([{food:paneer,grams}],200));
 for(const yieldGrams of [0,-1,NaN,Infinity,20001])assert.throws(()=>recipeNutrition([{food:paneer,grams:100}],yieldGrams));
 assert.throws(()=>recipeNutrition([],100));
});
test('requested staples and standalone illustrations resolve',()=>{
 for(const term of ['rice','oats','curd','butter','ghee','oil','paneer','soya'])assert.ok(catalog.extras.some(f=>(f.displayName||f.name).toLowerCase().includes(term)));
 for(const f of catalog.extras){assert.ok(existsSync(new URL('../dist/'+f.image,import.meta.url)));assert.equal(f.basisGrams,100);assert.ok(f.source);}
 assert.ok(catalog.templates.every(f=>f.estimated&&f.ingredients.length&&f.batchGrams>0));
});
