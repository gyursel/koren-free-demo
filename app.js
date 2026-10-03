'use strict';

// Initial catalog displayed while the live server catalog loads.
let PRODUCTS = [
  {id:'apples',name:'Български червени ябълки',category:'Плодове',price:2.49,oldPrice:null,unit:'1 кг',emoji:'🍎',tint:'#f3e9d7',badge:'Сезонно',image:'https://images.unsplash.com/photo-1568702846914-96b305d2aaeb?w=700&h=700&fit=crop&q=80',description:'Сочни и ароматни червени ябълки — за закуска, десерт или нещо вкусно по средата на деня.'},
  {id:'avocados',name:'Авокадо, готово за хапване',category:'Плодове',price:2.79,oldPrice:3.29,unit:'1 бр.',emoji:'🥑',tint:'#e7eddc',badge:'Специално',image:'https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=700&h=700&fit=crop&q=80',description:'Кремообразно авокадо, чудесно върху препечена филийка, в салата или домашно гуакамоле.'},
  {id:'tomatoes',name:'Розови домати',category:'Зеленчуци',price:3.99,oldPrice:null,unit:'1 кг',emoji:'🍅',tint:'#fae9df',badge:'Любим продукт',image:'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=700&h=700&fit=crop&q=80',description:'Сочни домати с познат аромат — съвършени за шопска салата и летни вечери.'},
  {id:'bread',name:'Хляб с квас и хрупкава коричка',category:'Пекарна',price:3.49,oldPrice:null,unit:'1 бр. · 500 г',emoji:'🥖',tint:'#f4ebdc',badge:'Препоръчано',image:'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=700&h=700&fit=crop&q=80',description:'Вдъхновен от традиционната пекарна — плътен вкус и ароматна хрупкава коричка.'},
  {id:'bananas',name:'Банани',category:'Плодове',price:2.19,oldPrice:null,unit:'1 кг',emoji:'🍌',tint:'#f3eed7',badge:'',image:'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=700&h=700&fit=crop&q=80',description:'Естествено сладки банани за лесна закуска, смути или домашен бананов хляб.'},
  {id:'lettuce',name:'Свежа зелена салата',category:'Зеленчуци',price:1.89,oldPrice:null,unit:'1 бр.',emoji:'🥬',tint:'#e7f0dd',badge:'Свежо',image:'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=700&h=700&fit=crop&q=80',description:'Хрупкави листа, които придават свежест на салати, сандвичи и всяко хранене.'},
  {id:'milk',name:'Прясно краве мляко',category:'Млечни',price:1.79,oldPrice:null,unit:'1 л',emoji:'🥛',tint:'#e9eeed',badge:'',image:'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=700&h=700&fit=crop&q=80',description:'Чудесен избор за сутрешното кафе, домашни десерти и любими семейни рецепти.'},
  {id:'strawberries',name:'Ароматни ягоди',category:'Плодове',price:4.49,oldPrice:4.99,unit:'500 г',emoji:'🍓',tint:'#f8e9e6',badge:'Специално',image:'https://images.unsplash.com/photo-1464965911861-746a04b4bca6?w=700&h=700&fit=crop&q=80',description:'Сладки ягоди, които носят настроение сами по себе си или като добавка към любимия десерт.'},
  {id:'cheese',name:'Бяло саламурено сирене',category:'Млечни',price:5.49,oldPrice:null,unit:'400 г',emoji:'🧀',tint:'#f6f0da',badge:'',image:'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=700&h=700&fit=crop&q=80',description:'Класически вкус за салати, баница или просто с топъл хляб и домат.'},
  {id:'oranges',name:'Сладки портокали',category:'Плодове',price:2.89,oldPrice:null,unit:'1 кг',emoji:'🍊',tint:'#faebd7',badge:'',image:'https://images.unsplash.com/photo-1547514701-42782101795e?w=700&h=700&fit=crop&q=80',description:'Ярък цитрусов вкус — за свеж сок или слънчево начало на деня.'},
  {id:'honey',name:'Пчелен мед',category:'Други',price:6.99,oldPrice:null,unit:'350 г',emoji:'🍯',tint:'#f3e8cd',badge:'',image:'https://images.unsplash.com/photo-1587049352851-8d4e89133924?w=700&h=700&fit=crop&q=80',description:'Сладко допълнение към чай, кисело мляко и домашни закуски.'},
  {id:'coffee',name:'Ароматно кафе на зърна',category:'Други',price:9.90,oldPrice:null,unit:'250 г',emoji:'☕',tint:'#eee7dc',badge:'',image:'https://images.unsplash.com/photo-1447933601403-0c6688de566e?w=700&h=700&fit=crop&q=80',description:'Наситен аромат за онези малки моменти, в които денят започва по правилния начин.'}
];

const $ = selector => document.querySelector(selector);
const money = value => new Intl.NumberFormat('bg-BG',{style:'currency',currency:'EUR'}).format(value);
const storageKey = 'koren-live-cart-v1';
let apiAvailable = false;
let stripeEnabled = false;
let stripeTestMode = false;
const esc = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let cart = loadCart();
let activeFilter = 'Всички';
let searchTerm = '';
let sortMode = 'featured';
let lastFocusedElement = null;
let activeDialog = null;
let toastTimeout;

function loadCart(){
  try{
    const saved = JSON.parse(localStorage.getItem(storageKey)||'{}');
    if(!saved||typeof saved!=='object'||Array.isArray(saved))return {};
    const cleaned = {};
    for(const [id,qty] of Object.entries(saved)){
      if(PRODUCTS.some(p=>p.id===id) && Number.isInteger(qty) && qty>0 && qty<=99)cleaned[id]=qty;
    }
    return cleaned;
  }catch{return {};}
}
function saveCart(){try{localStorage.setItem(storageKey,JSON.stringify(cart));}catch{/* Private browsing may disable storage. */}}
function itemCount(){return Object.values(cart).reduce((a,b)=>a+b,0);}
function subtotal(){return PRODUCTS.reduce((sum,p)=>sum+p.price*(cart[p.id]||0),0);}
function shipping(){return subtotal()===0||subtotal()>=45?0:3.90;}
function total(){return subtotal()+shipping();}
function findProduct(id){return PRODUCTS.find(p=>p.id===id);}
function badgeMarkup(product){return product.badge?`<span class="product-badge ${product.oldPrice?'sale':''}">${esc(product.badge)}</span>`:'';}
function imgMarkup(product,className='product-image'){
  return `<img class="${className}" src="${esc(product.image)}" alt="${esc(product.name)}" loading="lazy" decoding="async" referrerpolicy="no-referrer">`;
}

function renderProducts(){
  const filtered=PRODUCTS.filter(p=>{
    const categoryMatches=activeFilter==='Всички'||p.category===activeFilter;
    const text=`${esc(p.name)} ${esc(p.category)} ${esc(p.description)}`.toLocaleLowerCase('bg');
    return categoryMatches&&text.includes(searchTerm);
  });
  if(sortMode==='priceAsc')filtered.sort((a,b)=>a.price-b.price);
  else if(sortMode==='priceDesc')filtered.sort((a,b)=>b.price-a.price);
  else if(sortMode==='name')filtered.sort((a,b)=>a.name.localeCompare(b.name,'bg'));
  $('#productGrid').innerHTML=filtered.map(p=>`
    <article class="product-card">
      <div class="product-image-area"><button class="product-image-button" type="button" data-detail="${esc(p.id)}" aria-label="Разгледай ${esc(p.name)}">
        <span class="product-image-wrap" style="--tint:${esc(p.tint)}">
          <span class="product-emoji" aria-hidden="true">${esc(p.emoji)}</span>${imgMarkup(p)}${badgeMarkup(p)}
        </span>
      </button>
      <button class="quick-add" type="button" ${p.stock<=0?'disabled title="Изчерпан"':''} data-add="${esc(p.id)}" aria-label="Добави ${esc(p.name)} в количката" title="Добави в количката">+</button></div>
      <div class="product-details"><p class="product-category">${esc(p.category)}</p><button class="product-title" type="button" data-detail="${esc(p.id)}">${esc(p.name)}</button>
        <div class="product-bottom"><span><strong class="product-price">${money(p.price)}</strong>${p.oldPrice?`<span class="product-old-price">${money(p.oldPrice)}</span>`:''}</span><span class="product-unit">${esc(p.unit)}</span></div>
      </div>
    </article>`).join('');
  $('#resultsCount').textContent=filtered.length===1?'Показан е 1 продукт':`Показани са ${filtered.length} продукта`;
  $('#noResults').hidden=filtered.length!==0;
}
function setFilter(filter){
  activeFilter=filter;
  document.querySelectorAll('[data-filter]').forEach(button=>{
    const selected=button.dataset.filter===filter;
    button.classList.toggle('selected',selected);
    button.setAttribute('aria-pressed',String(selected));
  });
  renderProducts();
}
function showToast(message){
  const toast=$('#toast');toast.textContent=message;toast.classList.add('show');
  clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>toast.classList.remove('show'),2400);
}
function addToCart(id){
  const product=findProduct(id);if(!product)return;
  if(!apiAvailable){showToast('Няма връзка със сървъра. Опитай след малко.');return;}
  if((cart[id]||0)>=Math.min(99,product.stock)){showToast('Няма достатъчна наличност за този продукт.');return;}
  cart[id]=(cart[id]||0)+1;saveCart();renderCart();showToast(`${product.name} е добавен в количката.`);
}
function updateQuantity(id,difference){
  if(!findProduct(id))return;
  const next=(cart[id]||0)+difference;
  const product=findProduct(id);
  if(next<=0)delete cart[id];else if(next>product.stock){showToast('Няма достатъчна наличност.');return;}else cart[id]=Math.min(next,99);
  saveCart();renderCart();
}
function removeItem(id){delete cart[id];saveCart();renderCart();}
function renderCart(){
  const count=itemCount();$('#cartCount').textContent=count;$('#drawerItemCount').textContent=`(${count})`;
  const items=PRODUCTS.filter(p=>cart[p.id]);
  $('#cartItems').innerHTML=items.length?items.map(p=>`
    <div class="cart-row"><div class="cart-thumb" style="--tint:${esc(p.tint)}"><span aria-hidden="true">${esc(p.emoji)}</span>${imgMarkup(p,'cart-product-image')}</div>
    <div class="cart-row-info"><h3>${esc(p.name)}</h3><p>${esc(p.unit)}</p><div class="quantity-controls"><button type="button" data-qty="-1" data-id="${esc(p.id)}" aria-label="Намали броя на ${esc(p.name)}">−</button><span>${cart[p.id]}</span><button type="button" data-qty="1" data-id="${esc(p.id)}" aria-label="Увеличи броя на ${esc(p.name)}">+</button></div><button type="button" class="remove-item" data-remove="${esc(p.id)}">Премахни</button></div>
    <strong class="cart-row-price">${money(p.price*cart[p.id])}</strong></div>`).join(''):`<div class="empty-cart"><span class="empty-cart-icon" aria-hidden="true">🧺</span><h3>Количката ти е празна</h3><p>Добави нещо свежо и вкусно, за да започнеш.</p><button type="button" id="keepShopping" class="button button-secondary">Към продуктите ↗</button></div>`;
  $('#subtotal').textContent=money(subtotal());$('#delivery').textContent=count===0?'—':shipping()===0?'Безплатна':money(shipping());$('#total').textContent=money(total());
  $('#checkoutButton').disabled=count===0||!apiAvailable;
  const left=Math.max(0,45-subtotal());
  $('#shippingProgress').innerHTML=count===0?'Безплатна доставка при поръчка над 45 €':left>0?`Добави още <strong>${money(left)}</strong> за безплатна доставка<div class="progress-track"><div class="progress-fill" style="width:${Math.min(100,subtotal()/45*100)}%"></div></div>`:'✳ Получаваш безплатна доставка!';
}

function showOverlay(){ $('#overlay').hidden=false;document.body.classList.add('modal-open'); }
function hideOverlay(){ $('#overlay').hidden=true;document.body.classList.remove('modal-open'); }
function openCart(){
  closeModal(false);
  lastFocusedElement=document.activeElement;
  $('#cartDrawer').classList.add('open');$('#cartDrawer').setAttribute('aria-hidden','false');
  activeDialog=$('#cartDrawer');showOverlay();$('#closeCart').focus();
}
function closeCart(restoreFocus=true){
  $('#cartDrawer').classList.remove('open');$('#cartDrawer').setAttribute('aria-hidden','true');
  if(activeDialog===$('#cartDrawer')){activeDialog=null;hideOverlay();}
  if(restoreFocus&&lastFocusedElement instanceof HTMLElement)lastFocusedElement.focus();
}
function openModal(id){
  closeCart(false);closeModal(false);
  const dialog=$(id);lastFocusedElement=document.activeElement;
  dialog.classList.add('open');dialog.setAttribute('aria-hidden','false');activeDialog=dialog;showOverlay();
  dialog.querySelector('.modal-close')?.focus();
}
function closeModal(restoreFocus=true){
  ['#productModal','#checkoutModal'].forEach(id=>{const dialog=$(id);dialog.classList.remove('open');dialog.setAttribute('aria-hidden','true');});
  if(activeDialog&&activeDialog!==$('#cartDrawer')){activeDialog=null;hideOverlay();}
  if(restoreFocus&&lastFocusedElement instanceof HTMLElement)lastFocusedElement.focus();
}
function closeEverything(){if(activeDialog===$('#cartDrawer'))closeCart();else if(activeDialog)closeModal();}
function openProductDetail(id){
  const p=findProduct(id);if(!p)return;
  $('#modalProductContent').innerHTML=`<div class="modal-product"><div class="modal-product-image" style="--tint:${esc(p.tint)}"><span aria-hidden="true">${esc(p.emoji)}</span>${imgMarkup(p,'modal-product-photo')}</div><div class="modal-product-content"><p class="eyebrow">${p.category.toLocaleUpperCase('bg')}</p><h2 id="modalProductTitle">${esc(p.name)}</h2><p>${esc(p.description)}</p><p>Разфасовка: ${esc(p.unit)}</p><div class="modal-price">${money(p.price)} ${p.oldPrice?`<small><del>${money(p.oldPrice)}</del></small>`:''}</div><button type="button" class="button button-primary" ${p.stock<=0?'disabled':''} data-add="${esc(p.id)}">${p.stock<=0?'Изчерпан':'Добави в количката'} <span>↗</span></button></div></div>`;
  openModal('#productModal');
}
function openCheckout(){
  if(itemCount()===0)return;
  if(!apiAvailable){showToast('Няма връзка със сървъра.');return;}
  $('#checkoutForm').hidden=false;$('#checkoutSuccess').hidden=true;$('#checkoutForm').reset();
  $('#stripeMethodNote').hidden=true;$('#checkoutForm [type=submit]').textContent='Изпрати поръчката ↗';
  $('#checkoutError').textContent='';
  $('#checkoutTotal').textContent=money(total());openModal('#checkoutModal');
}
function resetFilters(){searchTerm='';$('#productSearch').value='';setFilter('Всички');$('#sortProducts').value='featured';sortMode='featured';renderProducts();}

// Delegate product and cart controls because the catalog is re-rendered after filtering.
document.addEventListener('click',event=>{
  const add=event.target.closest('[data-add]');if(add){addToCart(add.dataset.add);return;}
  const detail=event.target.closest('[data-detail]');if(detail){openProductDetail(detail.dataset.detail);return;}
  const filter=event.target.closest('[data-filter]');if(filter){setFilter(filter.dataset.filter);return;}
  const category=event.target.closest('[data-category]');if(category){setFilter(category.dataset.category);$('#products').scrollIntoView({behavior:'smooth'});return;}
  const qty=event.target.closest('[data-qty]');if(qty){updateQuantity(qty.dataset.id,Number(qty.dataset.qty));return;}
  const remove=event.target.closest('[data-remove]');if(remove){removeItem(remove.dataset.remove);return;}
});
document.addEventListener('error',event=>{
  const img=event.target;
  if(img.tagName==='IMG'&&(img.classList.contains('product-image')||img.classList.contains('cart-product-image')||img.classList.contains('modal-product-photo'))){
    img.parentElement.classList.add('no-image');
  }
},true);
$('#productSearch').addEventListener('input',event=>{searchTerm=event.target.value.trim().toLocaleLowerCase('bg');renderProducts();});
$('#sortProducts').addEventListener('change',event=>{sortMode=event.target.value;renderProducts();});
$('#resetFilters').addEventListener('click',resetFilters);
$('#showAllCategories').addEventListener('click',resetFilters);
$('#searchToggle').addEventListener('click',()=>{$('#products').scrollIntoView({behavior:'smooth'});$('#productSearch').focus({preventScroll:true});});
$('#cartToggle').addEventListener('click',openCart);
$('#closeCart').addEventListener('click',()=>closeCart());
$('#overlay').addEventListener('click',closeEverything);
$('#closeProductModal').addEventListener('click',()=>closeModal());
$('#closeCheckout').addEventListener('click',()=>closeModal());
$('#checkoutButton').addEventListener('click',openCheckout);
$('#paymentMethod').addEventListener('change',()=>{
  const online=$('#paymentMethod').value==='stripe';
  $('#checkoutForm [type=submit]').textContent=online?'Продължи към Stripe ↗':'Изпрати поръчката ↗';
  $('#stripeMethodNote').hidden=!online;
});
$('#finishCheckout').addEventListener('click',()=>closeModal());
$('#cartItems').addEventListener('click',event=>{if(event.target.id==='keepShopping'){closeCart();$('#products').scrollIntoView({behavior:'smooth'});}});
$('#checkoutForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const form=event.currentTarget;if(!form.reportValidity())return;
  const button=form.querySelector('[type="submit"]');
  const data=new FormData(form);
  button.disabled=true;$('#checkoutError').textContent='';
  try{
    const res=await fetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      customer:{name:data.get('name'),email:data.get('email'),phone:data.get('phone'),address:data.get('address')},
      items:Object.entries(cart).map(([id,quantity])=>({id,quantity})),payment_method:data.get('payment_method')||'cod'
    })});
    const order=await res.json().catch(()=>({}));
    if(!res.ok){const reason=Array.isArray(order.detail)?order.detail.map(e=>e.msg).join(', '):order.detail;throw Error(reason||'Поръчката не бе приета. Опитай отново.');}
    if(order.checkout_url){
      sessionStorage.setItem('koren-checkout-cart-snapshot', JSON.stringify(cart));
      window.location.assign(order.checkout_url);return;
    }
    $('#orderReference').textContent=order.id;
    cart={};saveCart();renderCart();form.reset();form.hidden=true;$('#checkoutSuccess').hidden=false;
  }catch(err){$('#checkoutError').textContent=err.message;}
  finally{button.disabled=false;}
});
$('#newsletterForm').addEventListener('submit',event=>{
  event.preventDefault();
  if(!$('#newsletterEmail').checkValidity()){$('#newsletterEmail').reportValidity();return;}
  $('#newsletterMessage').textContent='Демо: адресът е проверен, но не е записан или изпратен.';
  $('#newsletterEmail').value='';
});
$('#mobileToggle').addEventListener('click',()=>{
  const nav=$('#mobileNav');const wasOpen=!nav.hidden;nav.hidden=wasOpen;
  $('#mobileToggle').setAttribute('aria-expanded',String(!wasOpen));
});
document.querySelectorAll('#mobileNav a').forEach(link=>link.addEventListener('click',()=>{$('#mobileNav').hidden=true;$('#mobileToggle').setAttribute('aria-expanded','false');}));
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'){closeEverything();return;}
  if(event.key!=='Tab'||!activeDialog)return;
  const focusable=[...activeDialog.querySelectorAll('button:not(:disabled):not([hidden]),a[href],input:not([disabled]):not([hidden]),textarea:not([disabled]):not([hidden])')].filter(el=>el.getClientRects().length!==0);
  if(!focusable.length)return;
  const first=focusable[0],last=focusable[focusable.length-1];
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
});
$('#currentYear').textContent=new Date().getFullYear();
renderProducts();renderCart();

// Always replace the bootstrap examples with live server data before accepting orders.
async function loadLiveCatalog(){
  try{
    const [catalogResponse,configResponse]=await Promise.all([fetch('/api/products'),fetch('/api/config')]);
    if(!catalogResponse.ok||!configResponse.ok)throw Error('Сървърът не е достъпен.');
    const [catalog,config]=await Promise.all([catalogResponse.json(),configResponse.json()]);
    if(!Array.isArray(catalog))throw Error('Невалиден продуктов каталог.');
    PRODUCTS=catalog;apiAvailable=true;stripeEnabled=!!config.stripe_enabled;stripeTestMode=!!config.stripe_test_mode;
    const choice=$('#paymentMethod');
    if(stripeEnabled){choice.insertAdjacentHTML('beforeend',`<option value="stripe">💳 Плащане с карта${stripeTestMode?' (ТЕСТОВ РЕЖИМ)':''}</option>`);}
    cart=loadCart();
    for(const p of PRODUCTS){if(cart[p.id])cart[p.id]=Math.min(cart[p.id],p.stock);if(cart[p.id]===0)delete cart[p.id];}
    saveCart();renderProducts();renderCart();
    $('#serverStatus').textContent='Продуктите и наличностите се обновяват от магазина.';
    const flag=new URLSearchParams(window.location.search).get('checkout');
    if(flag==='return')await handleCheckoutReturn(new URLSearchParams(window.location.search).get('session_id'));
    else if(flag==='cancelled')paymentNotice('Плащането не е завършено. Поръчката не е потвърдена. Резервираната наличност се освобождава при изтичане на сесията.', 'pending');
  }catch(err){
    apiAvailable=false;PRODUCTS=[];cart={};renderProducts();renderCart();
    $('#serverStatus').textContent='Няма връзка със сървъра. Стартирай сайта с start-mac.command и обнови страницата.';
    $('#serverStatus').style.color='#ae4938';
  }
}
loadLiveCatalog();

// Always show status verified by our signed Stripe webhook, never infer payment
// from the browser redirect. A delayed webhook can make this temporarily pending.
function paymentNotice(message, state='pending'){
  const element=$('#paymentResult');
  element.textContent=message;
  element.dataset.state=state;
  element.hidden=false;
  element.scrollIntoView?.({behavior:'smooth',block:'start'});
}
async function handleCheckoutReturn(sessionId){
  if(!sessionId){paymentNotice('Върна се от платежната страница. Провери статуса на поръчката с магазина.','pending');return;}
  paymentNotice('Проверяваме потвърждението за плащане…','pending');
  for(let attempt=0;attempt<8;attempt++){
    try{
      const res=await fetch('/api/checkout/status?session_id='+encodeURIComponent(sessionId),{cache:'no-store'});
      if(!res.ok)throw Error('Няма достъпен статус.');
      const order=await res.json();
      if(order.payment_state==='paid'){
        paymentNotice(`✅ Плащането е потвърдено! Поръчка ${order.id} е приета.${stripeTestMode?' Това е ТЕСТОВО плащане.':''}`,'success');
        const snapshot=sessionStorage.getItem('koren-checkout-cart-snapshot');
        if(snapshot){
          try{for(const [id,quantity] of Object.entries(JSON.parse(snapshot))){
            if(cart[id]){cart[id]-=Math.min(cart[id],quantity);if(cart[id]<=0)delete cart[id];}
          }saveCart();renderCart();}catch(_){}
        }
        sessionStorage.removeItem('koren-checkout-cart-snapshot');
        await loadCatalogAfterPayment();
        return;
      }
      if(order.payment_state==='unpaid'||order.payment_state==='failed'){
        paymentNotice('Не е получено успешно плащане. Ако си бил таксуван, свържи се с магазина, преди да правиш нова поръчка.','error');return;
      }
      if(order.payment_state==='review'){
        paymentNotice('Плащането се проверява ръчно. Свържи се с магазина, преди да правиш нова поръчка.','pending');return;
      }
    }catch(err){if(attempt===7){paymentNotice('Няма потвърждение от сървъра. Провери поръчката при администратора, преди да опиташ отново.','pending');return;}}
    if(attempt<7)await new Promise(resolve=>setTimeout(resolve,2000));
  }
  paymentNotice('Потвърждението се обработва. Не прави нова поръчка, преди да провериш статуса.','pending');
}
async function loadCatalogAfterPayment(){
  try{
    const response=await fetch('/api/products');
    if(response.ok){PRODUCTS=await response.json();renderProducts();}
  }catch(_){}
}
