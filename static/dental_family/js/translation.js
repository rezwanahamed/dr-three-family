(() => {
  const container = document.getElementById('google-translate-element');
  if (!container) return;
  const switcher = container.closest('.language-switch');
  const buttons = [...switcher.querySelectorAll('[data-language]')];
  const status = switcher.querySelector('[data-translation-status]');
  let loading = false;
  let observer;
  let timer;
  const preference = value => {
    try { localStorage.setItem('website-language', value); } catch (_) { /* Storage may be disabled. */ }
  };
  const active = language => buttons.forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.language === language));
  });
  const clearTranslation = () => {
    const domains = ['', ...location.hostname.split('.').map((_, index, parts) => '.' + parts.slice(index).join('.'))];
    domains.forEach(domain => {
      document.cookie = 'googtrans=; Max-Age=0; path=/' + (domain ? '; domain=' + domain : '');
    });
  };
  const failed = () => {
    loading = false;
    observer?.disconnect();
    clearTimeout(timer);
    status.hidden = false;
    status.textContent = 'Translation unavailable. Select বাংলা to retry.';
  };
  const translate = () => {
    const select = container.querySelector('select');
    if (!select || !select.querySelector('option[value="bn"]')) return false;
    select.value = 'bn';
    select.dispatchEvent(new Event('change', { bubbles: true }));
    observer?.disconnect();
    clearTimeout(timer);
    loading = false;
    status.hidden = true;
    active('bn');
    preference('bn');
    return true;
  };
  const bangla = () => {
    if (translate() || loading) return;
    document.documentElement.classList.add('site-translation-active');
    loading = true;
    status.hidden = false;
    status.textContent = 'Translating…';
    observer = new MutationObserver(translate);
    observer.observe(container, { childList: true, subtree: true });
    timer = setTimeout(failed, 15000);
    window.googleTranslateElementInit = () => {
      try {
        new window.google.translate.TranslateElement({
          pageLanguage: 'en', includedLanguages: 'bn', autoDisplay: false,
        }, 'google-translate-element');
      } catch (_) { failed(); }
    };
    document.getElementById('google-translate-script')?.remove();
    const script = document.createElement('script');
    script.id = 'google-translate-script';
    script.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    script.async = true;
    script.onerror = failed;
    document.head.appendChild(script);
  };
  buttons.forEach(button => button.addEventListener('click', () => {
    if (button.dataset.language === 'bn') return bangla();
    preference('en');
    clearTranslation();
    if (loading || buttons.some(item => item.dataset.language === 'bn' && item.getAttribute('aria-pressed') === 'true')) {
      location.reload();
    } else active('en');
  }));
  let saved = 'en';
  try { saved = localStorage.getItem('website-language') || 'en'; } catch (_) { /* Use English by default. */ }
  if (saved === 'bn') bangla();
  else clearTranslation();
})();
