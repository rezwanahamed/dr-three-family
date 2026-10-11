(() => {
  const password=document.querySelector('#login-password'),toggle=document.querySelector('#toggle-password'),submit=document.querySelector('#login-submit');
  toggle.addEventListener('click',()=>{const show=password.type==='password';password.type=show?'text':'password';toggle.textContent=show?'Hide':'Show';toggle.setAttribute('aria-label',show?'Hide password':'Show password');toggle.setAttribute('aria-pressed',String(show));});
  document.querySelector('#login-form').addEventListener('submit',()=>{submit.disabled=true;submit.textContent='Signing in…';});
  window.addEventListener('pageshow',()=>{submit.disabled=false;submit.innerHTML='Sign in <span aria-hidden="true">→</span>';});
})();
