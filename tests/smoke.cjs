// Run: node tests/smoke.cjs (no node modules required)
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const elements=new Map();
function stub(id){if(!elements.has(id))elements.set(id,{id,textContent:'',value:'',innerHTML:'',hidden:false,disabled:false,dataset:{},style:{},classList:{add(){},remove(){},toggle(){}},addEventListener(){},setAttribute(){},focus(){},scrollIntoView(){},reset(){},insertAdjacentHTML(){},checkValidity(){return true;},getClientRects(){return [1]}});return elements.get(id);}
const document={querySelector:stub,querySelectorAll(){return []},addEventListener(){},activeElement:stub('focused'),body:{classList:{add(){},remove(){}}}};
const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../seed_products.json'),'utf8'));
const fakeCatalog=catalog.map(p=>({...p,stock:30}));
const context=vm.createContext({document,localStorage:{getItem(){return null},setItem(){}},Intl,Date,Number,Object,Math,JSON,String,URLSearchParams,
window:{location:{search:''}},fetch:async url=>({ok:true,json:async()=>url.includes('config')?{stripe_enabled:false}:fakeCatalog}),
setTimeout(){return 1},clearTimeout(){},HTMLElement:class{}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../app.js'),'utf8'),context,{filename:'app.js'});
setImmediate(()=>{
 assert.equal(vm.runInContext('PRODUCTS.length',context),12);
 assert.equal(vm.runInContext('apiAvailable',context),true);
 assert.equal(vm.runInContext('itemCount()',context),0);
 assert.match(stub('#productGrid').innerHTML,/Български червени ябълки/);
 vm.runInContext("addToCart('apples');addToCart('bread');",context);
 assert.equal(vm.runInContext('itemCount()',context),2);
 assert.equal(vm.runInContext('subtotal()',context),5.98);
 assert.equal(vm.runInContext('shipping()',context),3.90);
 assert.equal(vm.runInContext('total()',context),9.88);
 vm.runInContext("setFilter('Млечни')",context);
 assert.match(stub('#productGrid').innerHTML,/Прясно краве мляко/);
 assert.doesNotMatch(stub('#productGrid').innerHTML,/Български червени ябълки/);
 vm.runInContext('resetFilters()',context);
 vm.runInContext("updateQuantity('apples',-1);removeItem('bread')",context);
 assert.equal(vm.runInContext('itemCount()',context),0);
 console.log('PASS: live catalog, cart, totals, category filtering and reset');
});
