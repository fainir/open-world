// Private form state stays in this document; nothing goes into URL or analytics.
(() => {
  const form=document.getElementById('contact-form'),button=document.getElementById('submit-btn');
  const success=document.getElementById('success-msg'),error=document.getElementById('error-msg');
  let state;
  const payload=()=>Object.fromEntries(['name','email','message','website'].map(name=>[name,String(new FormData(form).get(name)||'').trim()]));
  form.addEventListener('submit',async event=>{
    event.preventDefault();event.stopImmediatePropagation();
    if(!form.reportValidity()||state?.busy)return;
    success.style.display='none';error.style.display='none';
    const value=payload(),signature=JSON.stringify(value);
    if(!state||state.signature!==signature){
      if(!crypto.randomUUID){error.textContent='This browser cannot send securely. Use the direct email link below.';error.style.display='block';return;}
      state={signature,key:crypto.randomUUID(),busy:false};
    }
    const sending=state;sending.busy=true;button.disabled=true;button.textContent='Saving…';
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);
    try{
      const response=await fetch('/api/contact',{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json','Idempotency-Key':sending.key},body:signature,signal:controller.signal});
      const result=await response.json().catch(()=>null);
      if(!response.ok||result?.status!=='stored')throw Error(response.status===429?'Please wait before retrying. Your text is kept here.':'We could not confirm your message was saved. Your text is kept here; retry or use direct email.');
      const unchanged=JSON.stringify(payload())===signature;
      if(unchanged)form.reset();state=undefined;
      success.textContent=result.notification==='accepted'?'Saved for the operator. The email service accepted its notification; inbox arrival and a reply time are not guaranteed.':'Saved for the operator. Its email notification is queued or awaiting delivery review; delivery is not yet confirmed.';
      if(!unchanged)success.textContent+=' Your newer edits remain here and have not been sent.';
      success.style.display='block';
    }catch(failure){error.textContent=failure.name==='AbortError'?'The request timed out. Your text is kept here; retry uses the same reference.':failure.message;error.style.display='block';}
    finally{clearTimeout(timer);sending.busy=false;button.disabled=false;button.textContent='Send message';}
  },true);
  button.disabled=false;
})();
