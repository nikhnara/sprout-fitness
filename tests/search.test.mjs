import test from 'node:test';import assert from 'node:assert/strict';
import {rankFoods,ndcg} from '../dist/search.mjs';
test('exact name outranks a frequent partial match',()=>{const a={id:'a',name:'Paneer'},b={id:'b',name:'Paneer curry'};assert.equal(rankFoods([b,a],'panner',{'2026-10-09':{meals:Array(100).fill({foodId:'b'})}})[0].id,'a');});
test('frequency is scoped to supplied diary and deletion removes preference',()=>{const f=[{id:'a',name:'Rice'},{id:'b',name:'Oats'}];assert.equal(rankFoods(f,'',{'2026-10-09':{meals:[{foodId:'b'}]}},'2026-10-09')[0].id,'b');assert.equal(rankFoods(f,'',{})[0].id,'a');});
test('NDCG recognizes ideal order and penalizes poor ordering',()=>{assert.equal(ndcg([3,2,1]),1);assert.ok(ndcg([1,2,3])<1);assert.equal(ndcg([]),0);});
