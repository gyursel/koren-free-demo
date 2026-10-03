'use strict';
const $=s=>document.querySelector(s);
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=cents=>new Intl.NumberFormat('bg-BG',{style:'currency',currency:'EUR'}).format(cents/100);
let csrf='',products=[],orders=[],editingId=null;
async function api(path,options={}){
  const response=await fetch(path,{credentials:'same-origin',...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRF-Token':csrf}:{}),...options.headers}});
  const data=await response.json().catch(()=>null);
  if(!response.ok){let detail=data?.detail;if(Array.isArray(detail))detail=detail.map(e=>e.msg).join(', ');throw Error(detail||`HTTP ${response.status}`);}
  return data;
}
function notice(message,isError=false){$('#notice').textContent=message;$('#notice').classList.toggle('error',isError);$('#notice').hidden=false;}
async function checkSession(){try{const me=await api('/api/admin/me');csrf=me.csrf;$('#loginScreen').hidden=true;$('#dashboard').hidden=false;await loadData();}catch(e){$('#loginScreen').hidden=false;$('#dashboard').hidden=true;}}
async function loadData(){try{[products,orders]=await Promise.all([api('/api/admin/products'),api('/api/admin/orders')]);refreshView();$('#notice').hidden=true;}catch(e){notice(e.message,true);}}
function tab(name){document.querySelectorAll('.nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));document.querySelectorAll('.tab').forEach(el=>el.hidden=el.id!=='tab-'+name);$('#pageTitle').textContent=({overview:'Преглед',products:'Продукти',orders:'Поръчки'})[name]||name;}
const STATUSES={new:'Нова',preparing:'Подготвя се',shipped:'Изпратена',completed:'Приключена',cancelled:'Отменена',awaiting_payment:'Очаква плащане',expired:'Изтекла',failed:'Неуспешна',payment_review:'Проверка на плащане'};
const PAYMENTS={cod_due:'При доставка',pending:'Очаква',paid:'Платена',unpaid:'Неплатена',failed:'Неуспешна',review:'Проверка'};
function orderCard(o){
 const editable=!['awaiting_payment','cancelled','expired','failed','payment_review','completed'].includes(o.status);
 return `<div class="order-card"><div class="order-top"><span class="order-id">${escapeHTML(o.id)}</span><span class="pill ${o.status==='new'?'':'warn'}">${escapeHTML(STATUSES[o.status]||o.status)}</span><strong>${money(o.total_cents)}</strong></div><div class="order-items">${o.items.map(i=>`${escapeHTML(i.product_name)} × ${i.quantity}`).join(' · ')}</div><div class="order-address">${escapeHTML(o.name)} · ${escapeHTML(o.email)} · ${escapeHTML(o.phone)} · ${escapeHTML(o.address)}</div><div class="order-bottom"><small>${escapeHTML(o.created_at)} · ${o.method==='cod'?'Наложен платеж':'Stripe'} · ${escapeHTML(PAYMENTS[o.payment_state]||o.payment_state)}</small>${editable?`<div class="order-actions"><label>Статус <select data-order-status="${escapeHTML(o.id)}"><option value="new" ${o.status==='new'?'selected':''}>Нова</option><option value="preparing" ${o.status==='preparing'?'selected':''}>Подготвя се</option><option value="shipped" ${o.status==='shipped'?'selected':''}>Изпратена</option><option value="completed">Приключена</option><option value="cancelled">Отмени</option></select></label><button type="button" class="mini-btn" data-save-order="${escapeHTML(o.id)}">Запази</button></div>`:''}</div></div>`;
}
function refreshView(){
 $('#statProducts').textContent=products.filter(p=>p.active).length;
 $('#statNew').textContent=orders.filter(o=>o.status==='new').length;
 $('#statOrders').textContent=orders.length;
 $('#statStock').textContent=products.filter(p=>p.active&&p.stock<=5).length;
 $('#recentOrders').innerHTML=orders.slice(0,3).map(orderCard).join('')||'<p class="empty">Все още няма поръчки.</p>';
 $('#productsBody').innerHTML=products.map(p=>`<tr><td><span class="product-cell"><span class="thumb">${escapeHTML(p.emoji)}</span><span>${escapeHTML(p.name)}</span></span></td><td>${escapeHTML(p.category)}</td><td>${money(Math.round(p.price*100))}</td><td><span class="pill ${p.stock<=5?'warn':''}">${p.stock}</span></td><td><span class="pill ${p.active?'':'off'}">${p.active?'Активен':'Скрит'}</span></td><td><button class="mini-btn" data-edit="${escapeHTML(p.id)}">Редакция</button></td></tr>`).join('');
 $('#ordersList').innerHTML=orders.map(orderCard).join('')||'<p class="empty">Все още няма поръчки.</p>';
}
function showEditor(id){
 const p=products.find(p=>p.id===id);editingId=id||null;
 $('#editTitle').textContent=p?'Редактирай продукт':'Нов продукт';$('#editMessage').textContent='';
 const form=$('#productForm');form.reset();
 const data=p||{name:'',category:'Плодове',price:'',oldPrice:'',stock:0,unit:'1 бр.',emoji:'🛒',tint:'#e7eddc',badge:'',image:'',description:'',active:true};
 for(const [k,v] of Object.entries(data)){const field=form.elements.namedItem(k);if(!field)continue;if(field.type==='checkbox')field.checked=!!v;else field.value=v??'';}
 $('#editOverlay').hidden=false;form.elements.namedItem('name').focus();
}
function hideEditor(){$('#editOverlay').hidden=true;editingId=null;}
$('#loginForm').addEventListener('submit',async e=>{e.preventDefault();$('#loginMessage').textContent='';try{await api('/api/admin/login',{method:'POST',body:JSON.stringify({username:$('#loginUser').value,password:$('#loginPassword').value})});$('#loginPassword').value='';await checkSession();}catch(err){$('#loginMessage').textContent=err.message;}});
$('#logout').addEventListener('click',async()=>{try{await api('/api/admin/logout',{method:'POST'});}finally{csrf='';$('#dashboard').hidden=true;$('#loginScreen').hidden=false;}});
$('#refreshData').addEventListener('click',loadData);
document.addEventListener('click',async e=>{
 const nav=e.target.closest('[data-tab],[data-goto]');if(nav){tab(nav.dataset.tab||nav.dataset.goto);return;}
 const edit=e.target.closest('[data-edit]');if(edit){showEditor(edit.dataset.edit);return;}
 const save=e.target.closest('[data-save-order]');if(save){const id=save.dataset.saveOrder;const select=save.parentElement.querySelector('select');if(select.value==='cancelled'&&!confirm('Да отменим ли поръчката и да върнем наличността?'))return;try{await api('/api/admin/orders/'+encodeURIComponent(id),{method:'PATCH',body:JSON.stringify({status:select.value})});await loadData();notice('Поръчката е актуализирана.');}catch(err){notice(err.message,true);}return;}
});
$('#addProduct').addEventListener('click',()=>showEditor());
$('#closeEdit').addEventListener('click',hideEditor);$('#cancelEdit').addEventListener('click',hideEditor);
$('#editOverlay').addEventListener('click',e=>{if(e.target===$('#editOverlay'))hideEditor();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#editOverlay').hidden)hideEditor();});
$('#productForm').addEventListener('submit',async e=>{
 e.preventDefault();const f=e.currentTarget;const get=k=>f.elements.namedItem(k).value.trim();const oldPrice=get('oldPrice');
 const payload={name:get('name'),category:get('category'),price:get('price'),oldPrice:oldPrice||null,stock:Number(get('stock')),unit:get('unit'),emoji:get('emoji'),tint:get('tint'),badge:get('badge'),image:get('image'),description:get('description'),active:f.elements.namedItem('active').checked};
 $('#editMessage').textContent='';const btn=f.querySelector('[type=submit]');btn.disabled=true;
 try{await api('/api/admin/products'+(editingId?'/'+encodeURIComponent(editingId):''),{method:editingId?'PUT':'POST',body:JSON.stringify(payload)});hideEditor();await loadData();notice('Продуктът е запазен.');}catch(err){$('#editMessage').textContent=err.message;}finally{btn.disabled=false;}
});
checkSession();
