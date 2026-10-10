import {keys,totals,localDate} from './core.mjs';
export const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const storageKey=uid=>{if(!uid)throw Error('A user is required');return 'gamna:diary:'+uid;};
export function csvCell(value){let s=String(value??'');if(/^[\s]*[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}
export function diaryCsv(state){const rows=[['Date','Type','Name','Meal','Grams','Calories (kcal)','Protein (g)','Fat (g)','Carbs (g)','Fiber (g)','Weight (kg)','Sleep (h)','Activity (min)']];for(const [date,d] of Object.entries(state.days).sort()){
rows.push([date,'Check-in','','','','','','','','',d.weight??'',d.sleep??'','']);
for(const m of d.meals)rows.push([date,'Food',m.name,m.meal,m.grams,...keys.map(k=>m.nutrients[k]??''),'','','']);
for(const e of d.exercise)rows.push([date,'Activity',e.name,'','','','','','','','','',e.minutes]);
}return '\ufeff'+rows.map(row=>row.map(csvCell).join(',')).join('\r\n');}
export function periodRows(days,date,length){const end=new Date(date+'T12:00:00');return Array.from({length},(_,i)=>{const dt=new Date(end);dt.setDate(dt.getDate()-length+1+i);const key=localDate(dt),d=days[key];return {date:key,weight:d?.weight??null,sleep:d?.sleep??null,minutes:d?.exercise?.length?d.exercise.reduce((s,e)=>s+e.minutes,0):null,...Object.fromEntries(keys.map(k=>[k,d?.meals?.length&&!totals(d.meals).missing.includes(k)?totals(d.meals)[k]:null]))};});}
export const poses=['Victory lap','Tiny flex','Stretch break','Disco warm-up','Balance mode','Power pose','Happy jog','Big reach','Side stretch','Champion wave','Squat squad','Rest-day dance'];
// Photos remain private profile pictures; they are never pasted into an avatar.
export function avatar(pose=0,photo=null,tone=null,hair=null){
 const i=((Math.floor(pose)%12)+12)%12;
 return `<span class="gamna-avatar rendered-companion" role="img" aria-label="Gamna companion: ${poses[i]}" style="background-position:${(i%4)*100/3}% ${Math.floor(i/4)*50}%"></span>`;
}
export function safeLink(url){try{const u=new URL(url);return u.protocol==='https:'?u.href:'#';}catch{return '#';}}
