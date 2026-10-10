import {normalizeSearch} from './personal.mjs';
export function preferenceIndex(days){
 const index=new Map();
 for(const [date,day] of Object.entries(days||{}))for(const m of day.meals||[]){
  const k=String(m.foodId),p=index.get(k)||{count:0,last:''};p.count++;if(date>p.last)p.last=date;index.set(k,p);
 }return index;
}
export function rankFoods(foods,query,days={},today=new Date().toISOString().slice(0,10)){
 const q=normalizeSearch(query),tokens=q.split(' ').filter(Boolean),prefs=preferenceIndex(days);
 return foods.map((food,order)=>{
  const name=normalizeSearch(food.displayName||food.name||''),text=normalizeSearch([food.name,food.displayName,food.aliases,food.brand,food.restaurant].filter(Boolean).join(' '));
  if(tokens.some(t=>!text.includes(t)))return null;
  const relevance=!q?0:name===q?1000:name.startsWith(q)?600:name.includes(q)?400:200;
  const p=prefs.get(String(food.id)),age=p?Math.max(0,(Date.parse(today)-Date.parse(p.last))/86400000):Infinity;
  const personal=p?Math.min(60,15*Math.log2(1+p.count))+20*Math.exp(-age/14):0;
  return {food,order,score:relevance+personal};
 }).filter(Boolean).sort((a,b)=>b.score-a.score||a.order-b.order).map(x=>x.food);
}
// Offline relevance judgments only, not a claim that live relevance is measured.
export function ndcg(relevances,k=10){
 const dcg=a=>a.slice(0,k).reduce((s,r,i)=>s+(2**r-1)/Math.log2(i+2),0);
 const ideal=dcg([...relevances].sort((a,b)=>b-a));return ideal?dcg(relevances)/ideal:0;
}
