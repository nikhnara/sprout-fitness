// Historical USDA records retain their release date; current menu records have independent IDs.
export const chains=[['McDonald’s','mcdonald'],['Burger King','burger king'],['Wendy’s','wendy'],['Taco Bell','taco bell'],['Chick-fil-A','chick-fil'],['Subway','subway'],['KFC','kfc'],['Pizza Hut','pizza hut'],['Domino’s','domino'],['Popeyes','popeye'],['Chipotle','chipotle']];
export function restaurantName(food){return food.restaurant||chains.find(([,q])=>food.name.toLowerCase().includes(q))?.[0]||null;}
const sourceUrl='https://www.chipotle.com/content/dam/chipotle/menu/nutrition/US-Nutrition-Facts-Paper-Menu-3-2025.pdf';
const items=[
 ['Cilantro-lime brown rice',4,210,4,6,36,2,'plant'],['Cilantro-lime white rice',4,210,4,4,40,1,'plant'],
 ['Black beans',4,130,8,1.5,22,7,'plant'],['Pinto beans',4,130,8,1.5,21,8,'plant'],
 ['Fajita vegetables',2,20,1,0,5,1,'plant'],['Sofritas',4,150,8,10,9,3,'plant'],
 ['Chicken',4,180,32,7,0,0,'other'],['Steak',4,150,21,6,1,1,'other'],['Carnitas',4,210,23,12,0,0,'other'],['Barbacoa',4,170,24,7,2,1,'other'],
 ['Fresh tomato salsa',4,25,0,0,4,1,'plant'],['Roasted chili-corn salsa',4,80,3,1.5,16,3,'plant'],
 ['Cheese',1,110,6,8,1,0,'dairy'],['Sour cream',2,110,2,9,2,0,'dairy'],
 ['Guacamole',4,230,2,22,8,6,'plant'],['Queso blanco',2,120,5,9,4,0,'dairy'],
 ['Supergreens salad mix',3,15,1,0,3,2,'plant'],['Romaine lettuce',1,5,0,0,1,1,'plant'],['Chips',4,540,7,25,73,7,'plant']];
export const restaurantFoods=items.map(([name,oz,kcal,protein,fat,carbs,fiber,diet])=>{
 const grams=oz*28.349523125;
 return {id:'restaurant-chipotle-us-2025-'+name.toLowerCase().replace(/[^a-z0-9]+/g,'-'),name:'Chipotle · '+name,restaurant:'Chipotle',market:'US',diet,category:'Restaurant',source:'Chipotle US menu · March 2025',sourceUrl,verifiedAt:'2026-10-09',basisGrams:100,defaultGrams:grams,portions:[{label:`1 menu portion (${oz} oz)`,grams}],note:'US standard menu portion. Restaurant scoops vary; this source is dated March 2025. Weigh or change quantities for your order. Not a complete current menu.',nutrients:Object.fromEntries(Object.entries({kcal,protein,fat,carbs,fiber}).map(([k,v])=>[k,v*100/grams]))};
});
