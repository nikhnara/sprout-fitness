import {test} from 'node:test';
import assert from 'node:assert/strict';
import {scale,totals,weightTrend,averageWeight} from '../dist/core.mjs';
import {readFileSync} from 'node:fs';
test('scales weighed portions without losing unknown nutrients',()=>{assert.deepEqual(scale({kcal:100,protein:20,fat:2,carbs:5,fiber:null},150),{kcal:150,protein:30,fat:3,carbs:7.5,fiber:null});assert.throws(()=>scale({},-1));assert.throws(()=>scale({},NaN));});
test('totals distinguish a missing nutrient from a measured zero',()=>{const result=totals([{nutrients:{kcal:100,protein:5,fat:0,carbs:20,fiber:null}},{nutrients:{kcal:40,protein:2,fat:0,carbs:8,fiber:1}}]);assert.equal(result.kcal,140);assert.equal(result.fiber,1);assert.deepEqual(result.missing,['fiber']);});
test('weight changes and weekly averages exclude missing entries',()=>{const d={'2026-10-01':{weight:80},'2026-10-02':{weight:null},'2026-10-04':{weight:79}};assert.equal(weightTrend(d,'2026-10-04').delta,-1);assert.equal(weightTrend(d,'2026-10-01'),null);assert.deepEqual(averageWeight(d,'2026-10-01','2026-10-07'),{value:79.5,count:2});});
test('source catalog has complete provenance, sane portions and nullable nutrients',()=>{const foods=JSON.parse(readFileSync(new URL('../dist/foods.json',import.meta.url)));assert.equal(foods.length,7793);assert.equal(new Set(foods.map(f=>f.id)).size,foods.length);for(const f of foods){assert.equal(f.basisGrams,100);assert.ok(f.sourceUrl.includes(f.id));for(const p of f.portions)assert.ok(p.grams>0);for(const v of Object.values(f.nutrients))assert.ok(v===null||(Number.isFinite(v)&&v>=0));}});
