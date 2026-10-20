(() => {
  const root=document.querySelector('[data-pricing-calculator]');if(!root)return;
  const data=JSON.parse(document.querySelector('#pricing-calculator-data').textContent),form=root.querySelector('form');
  const serviceSelect=form.elements.calculator_service,priceSelect=form.elements.calculator_price,quantity=form.elements.calculator_quantity;
  const add=form.querySelector('[type="submit"]'),hint=root.querySelector('[data-price-hint]'),status=root.querySelector('[data-calculator-status]');
  const list=root.querySelector('[data-calculator-items]'),cart=new Map();
  const money=cents=>new Intl.NumberFormat('en-BD',{maximumFractionDigits:2}).format(cents/100);
  const range=(min,max)=>min===max?`${money(min)} Tk`:`${money(min)}–${money(max)} Tk`;
  const service=()=>data.services.find(s=>s.id===serviceSelect.value);
  const selected=()=>service()?.prices.find(p=>p.id===priceSelect.value);
  function updatePrice(){const price=selected();add.disabled=!price;hint.textContent=price?`${price.treatment_id?'Published treatment price':'Published service price'}: ${price.label}`:'Select a published treatment or service price.';}
  serviceSelect.onchange=()=>{const prices=service()?.prices||[];priceSelect.replaceChildren(new Option(prices.length?'Choose a treatment or service price':'No published prices for this service',''));for(const price of prices)priceSelect.add(new Option(`${price.title} — ${price.label}`,price.id));const serviceOnly=prices.length===1&&!prices[0].treatment_id;
    // A service fee can be estimated directly even when its treatments have no prices.
    if(serviceOnly)priceSelect.value=prices[0].id;
    priceSelect.disabled=!prices.length||serviceOnly;
    status.textContent=serviceOnly?'Using the service price. Enter a quantity and add it to your estimate.':prices.length?'':'Please contact the clinic for an estimate for this service.';updatePrice();};
  priceSelect.onchange=updatePrice;
  function draw(){
    list.replaceChildren();let min=0,max=0,known=0,unquoted=0;
    for(const [id,item] of cart){
      const row=document.createElement('li'),copy=document.createElement('div'),title=document.createElement('strong'),details=document.createElement('span'),remove=document.createElement('button');
      title.textContent=item.title;details.textContent=`${item.quantity} × ${item.label}`;copy.append(title,details);
      remove.type='button';remove.textContent='Remove';remove.setAttribute('aria-label',`Remove ${item.title}`);remove.onclick=()=>{cart.delete(id);draw();};row.append(copy,remove);list.append(row);
      if(item.min===null){unquoted++;}else{known++;min+=item.min*item.quantity;max+=item.max*item.quantity;}
    }
    root.querySelector('[data-calculator-empty]').hidden=cart.size>0;
    root.querySelector('[data-total-label]').textContent=unquoted&&known?'Known subtotal':'Estimated total';
    root.querySelector('[data-calculator-total]').textContent=known?range(min,max):cart.size?'Contact for estimate':'—';
    root.querySelector('[data-quote-note]').textContent=unquoted?`${unquoted} selected item${unquoted===1?' requires':'s require'} a separate quote${known?` and ${unquoted===1?'is':'are'} excluded from this subtotal`:''}.`:'';
  }
  form.onsubmit=event=>{event.preventDefault();if(!form.reportValidity())return;const price=selected(),count=Number(quantity.value);if(!price||!Number.isInteger(count)||count<1||count>99)return;
    if(!cart.has(price.id)&&cart.size>=50){status.textContent='Use at most 50 items in one estimate.';return;}
    const total=(cart.get(price.id)?.quantity||0)+count;if(total>99){status.textContent='Use at most 99 units of each item.';return;}
    cart.set(price.id,{...price,quantity:total});draw();quantity.value='1';status.textContent=`Added ${price.title} to your estimate.`;
  };
  draw();
})();
