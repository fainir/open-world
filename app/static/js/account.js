(() => {
  const $=id=>document.getElementById(id),dialog=$('confirmation');let busy=false;
  function message(text){$('status').textContent=text;}
  function signedOut(text){Auth.clearAuth();$('account').hidden=true;$('signed-out').hidden=false;message(text);}
  async function responseError(response){const data=await response.json().catch(()=>({}));return typeof data.detail==='string'?data.detail:'This action could not finish. Please try again.';}
  async function load(){
    $('retry-account').hidden=true;
    if(!Auth.isLoggedIn()){signedOut('You are not signed in.');return;}
    try{const response=await fetch('/api/auth/me',{headers:Auth.authHeaders(),cache:'no-store'});if(response.status===401){signedOut('Your session ended. Sign in again to manage this account.');return;}if(!response.ok)throw new Error(await responseError(response));const user=await response.json();$('profile').textContent=user.username+' · '+user.email;$('account').hidden=false;$('signed-out').hidden=true;message('Your saved account data is ready.');}
    catch{$('retry-account').hidden=false;message('Your account could not load. Try again when the connection is available.');}
  }
  $('retry-account').onclick=load;
  $('forget').onclick=()=>{localStorage.removeItem('ow_api_key');message('The saved API key was removed from this browser. Reload any other OpenWorld tabs to clear their in-memory copy.');};
  $('export').onclick=async()=>{
    const button=$('export');button.disabled=true;message('Preparing your download…');
    try{const response=await fetch('/api/account/export',{headers:Auth.authHeaders(),cache:'no-store'});if(response.status===401){signedOut('Your session ended. Sign in again before downloading.');return;}if(!response.ok)throw new Error(await responseError(response));const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='openworld-account.zip';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);message('Your account download started. Keep it somewhere private.');}
    catch(error){message(error.message||'Your download could not finish. Please try again.');}finally{button.disabled=false;}
  };
  $('delete').onclick=()=>{$('delete-status').textContent='';dialog.showModal();$('cancel').focus();};
  $('cancel').onclick=()=>dialog.close();
  dialog.addEventListener('cancel',event=>{if(busy)event.preventDefault();});
  dialog.addEventListener('close',()=>{$('delete-form').reset();$('delete-status').textContent='';if(!$('account').hidden)$('delete').focus();});
  dialog.addEventListener('keydown',event=>{if(event.key!=='Tab')return;const controls=[...dialog.querySelectorAll('button,input')].filter(el=>!el.disabled&&el.getClientRects().length);const current=controls.indexOf(document.activeElement);if(event.shiftKey&&current<=0){event.preventDefault();controls.at(-1)?.focus();}else if(!event.shiftKey&&(current<0||current===controls.length-1)){event.preventDefault();controls[0]?.focus();}});
  $('delete-form').onsubmit=async event=>{
    event.preventDefault();if(busy||!event.target.reportValidity())return;busy=true;$('submit-delete').disabled=true;$('cancel').disabled=true;$('password').readOnly=true;$('confirm').readOnly=true;$('delete-status').textContent='Closing your account…';
    try{const response=await fetch('/api/account/delete',{method:'POST',headers:{...Auth.authHeaders(),'Content-Type':'application/json'},body:JSON.stringify({password:$('password').value,confirm:$('confirm').value})});if(response.status===401){dialog.close();signedOut('Your session ended. Sign in again to check this account.');return;}if(!response.ok)throw new Error(await responseError(response));for(const key of Object.keys(localStorage))if(key.startsWith('ow_'))localStorage.removeItem(key);dialog.close();signedOut('Your account and its active website data were removed. Recovery copies are handled as described in Privacy.');}
    catch(error){$('delete-status').textContent=error.message||'Account closure could not finish. Please try again.';}finally{busy=false;$('submit-delete').disabled=false;$('cancel').disabled=false;$('password').readOnly=false;$('confirm').readOnly=false;}
  };
  load();
})();
