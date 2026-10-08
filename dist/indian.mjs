import {keys,scale,totals} from './core.mjs';
export function recipeNutrition(ingredients,batchGrams){
 if(!Number.isFinite(batchGrams)||batchGrams<=0||batchGrams>20000)throw Error('Enter a finished batch weight between 1 and 20,000 g.');
 if(!ingredients.length)throw Error('Add at least one ingredient.');
 const t=totals(ingredients.map(x=>({nutrients:scale(x.food.nutrients,x.grams)})));
 return Object.fromEntries(keys.map(k=>[k,t.missing.includes(k)?null:t[k]*100/batchGrams]));
}
export function indianCatalog(catalog){
 const picture=name=>'assets/foods/'+name+'.png';
 const map=new Map(catalog.map(f=>[f.id,f]));
 const basic=(id,name,g,img,aliases='')=>({...structuredClone(map.get(id)),displayName:name,defaultGrams:g,image:picture(img),aliases});
 const staples=[basic('168878','Rice · cooked',200,'rice'),basic('169705','Rolled oats · dry',50,'oats-dry'),basic('171284','Curd · plain whole milk',150,'curd','dahi yogurt yoghurt'),basic('173410','Butter · salted',5,'butter'),basic('173412','Ghee · butterfat reference',5,'ghee','clarified butter'),basic('172336','Oil · canola',5,'oil','cooking oil vegetable'),basic('171413','Oil · olive',5,'oil')].filter(f=>f.id);
 const paneer={id:'brand-amul-paneer',name:'Amul Malai paneer',displayName:'Paneer · Amul Malai',aliases:'panner cottage cheese',diet:'dairy',basisGrams:100,defaultGrams:100,image:picture('paneer'),source:'Amul manufacturer nutrition label',sourceUrl:'https://old.amul.com/products/amul-malaipaneer-info.php',note:'Amul Malai paneer label. Homemade and other brands differ; fiber is not quantified on this label.',nutrients:{kcal:323,protein:20,fat:25,carbs:4.5,fiber:null}};
 const soya={id:'brand-bon-soya',name:'Bon Vegan soya chunks · dry',displayName:'Soya chunks · dry',aliases:'soy nutrela meal maker textured protein',diet:'plant',basisGrams:100,defaultGrams:30,image:picture('soya'),source:'Bon Vegan manufacturer catalogue, p. 33',sourceUrl:'https://bon-vegan.com/wp-content/uploads/2024/04/Bon-Vegan_-full_catalogue.pdf#page=33',note:'Bon Vegan dry soya chunks, not a verified Nutrela label. Weigh before soaking. EU available carbohydrate 27 g + fiber 8.8 g are combined to approximate the total-carbohydrate basis used in this tracker. Check your own packet.',nutrients:{kcal:332,protein:49,fat:1.2,carbs:35.8,fiber:8.8}};
 const extras=[...staples,paneer,soya];extras.forEach(f=>map.set(f.id,f));
 const recipe=(id,name,img,weight,portion,items)=>{
  if(items.some(([id])=>!map.has(id)))return null;
  const ingredients=items.map(([id,grams])=>({food:structuredClone(map.get(id)),grams}));
  return {id:'template-'+id,name:name+' · editable recipe',displayName:name,aliases:name,diet:ingredients.some(x=>x.food.diet==='dairy')?'dairy':'plant',image:picture(img),source:'Modeled recipe · ingredient records',basisGrams:100,batchGrams:weight,defaultGrams:portion,estimated:true,ingredients,portions:[{label:'Example serving',grams:portion}],note:'Example recipe, not a measured dish. Tap “Customize recipe” to set your ingredient amounts and finished cooked batch weight. Nutrition includes the listed oil; do not add that same oil twice.',nutrients:recipeNutrition(ingredients,weight)};
 };
 const templates=[
 recipe('chana','Chana masala','chana',650,250,[['173757',400],['170457',120],['170000',80],['172336',10],['170924',5]]),
 recipe('dal','Dal tadka','dal',600,200,[['172436',100],['170457',80],['170000',50],['173412',10],['170924',3]]),
 recipe('rajma','Rajma curry','rajma',650,250,[['173740',400],['170457',120],['170000',80],['172336',10],['170924',5]]),
 recipe('roti','Roti · no added fat','roti',160,40,[['168893',100]]),
 recipe('oatmeal','Oatmeal · cooked with water','oatmeal',250,250,[['169705',50]]),
 recipe('idli','Idli · rice & urad','idli',600,150,[['168931',150],['174259',50]]),
 recipe('dosa','Dosa · rice & urad','dosa',450,150,[['168931',150],['174259',50],['172336',10]])
 ].filter(Boolean);
 return {extras:[...extras,...templates],favorites:[...templates,...extras],templates};
}
