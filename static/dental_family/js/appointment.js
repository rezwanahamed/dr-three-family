(() => {
  const form = document.querySelector('#appointment-form');
  if (!form) return;
  const fields = form.querySelector('fieldset');
  const status = document.querySelector('#appointment-status');
  const button = form.querySelector('[type="submit"]');
  let busy = false;
  function message(text, error = false) {
    status.textContent = text;
    status.dataset.error = String(error);
  }
  function styleBranchDropdown() {
    const select = form.elements.chamber_address;
    const address = document.querySelector('#booking-branch-address');
    for (const option of select.options) {
      option.dataset.address = option.text;
      if (!option.value) continue;
      const parts = option.text.match(/^BRANCH\s*-?\s*(\d+)\s*:\s*(.*)$/i);
      const fullAddress = parts ? parts[2] : option.text;
      const locality = /chandgaon|bahaddarhat/i.test(fullAddress) ? 'Chandgaon · Bahaddarhat'
        : /parbartak|prabortak|panchalish|panchlaish/i.test(fullAddress) ? 'Prabortak · Panchlaish'
        : fullAddress.split(',')[0];
      const shortLabel = locality.length > 45 ? locality.slice(0, 42) + '…' : locality;
      option.text = parts ? `Branch ${parts[1]} — ${shortLabel}` : shortLabel;
      option.dataset.address = fullAddress;
    }
    const updateAddress = () => {
      const option = select.selectedOptions[0];
      address.textContent = option?.value ? option.dataset.address : 'Choose a branch, or leave this as no preference.';
    };
    select.addEventListener('change', updateAddress);
    form.addEventListener('reset', () => queueMicrotask(updateAddress));
    updateAddress();
  }
  async function readResponse(response) {
    const data = await response.json();
    if (!response.ok) throw Object.assign(new Error(data.error || 'Booking is unavailable. Please call the clinic.'), {data});
    return data;
  }
  fetch(form.dataset.endpoint, {credentials: 'same-origin', cache: 'no-store'})
    .then(readResponse).then(data => {
      for (const [name, options] of Object.entries(data.options)) {
        const select = form.elements.namedItem(name);
        for (const [value, label] of options) select.add(new Option(label, value));
      }
      styleBranchDropdown();
      form.elements.appointment_date.min = data.today;
      fields.disabled = false;
      message('Choose your preferred date and time. Fields marked * are required.');
    }).catch(() => message('Online booking is temporarily unavailable. Please open the booking portal below or call the clinic.', true));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || !form.reportValidity()) return;
    form.querySelectorAll('.booking-error').forEach(node => node.remove());
    form.querySelectorAll('[aria-invalid]').forEach(node => {node.removeAttribute('aria-invalid'); if (node.id === 'booking-branch') node.setAttribute('aria-describedby', 'booking-branch-address'); else node.removeAttribute('aria-describedby');});
    const payload = new FormData(form);
    const token = document.cookie.split('; ').find(value => value.startsWith('csrftoken='))?.slice(10) || '';
    busy = true; fields.disabled = true; button.textContent = 'Sending request…';
    message('Sending your appointment request. Please wait.');
    let completed = false;
    try {
      const response = await fetch(form.dataset.endpoint, {method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': decodeURIComponent(token)}, body: payload});
      const data = await readResponse(response);
      if (data.success !== true) throw Error('Unconfirmed response');
      completed = true;
      form.reset(); message(data.message);
      button.textContent = 'Request received';
    } catch (error) {
      // A lost response can follow a saved booking. Never retry automatically.
      const uncertain = !error.data || error.data.uncertain;
      completed = Boolean(uncertain);
      message(error.data?.error || 'We could not confirm the booking result. Please call the clinic before submitting again to avoid a duplicate.', true);
      for (const [name, errors] of Object.entries(error.data?.errors || {})) {
        const input = form.elements.namedItem(name);
        if (!input) continue;
        const node = document.createElement('p');
        node.id = `${input.id}-error`; node.className = 'booking-error';
        node.textContent = errors.join(' '); input.after(node);
        input.setAttribute('aria-invalid', 'true'); input.setAttribute('aria-describedby', name === 'chamber_address' ? `booking-branch-address ${node.id}` : node.id);

      }
      button.textContent = uncertain ? 'Please contact the clinic' : 'Request appointment →';
    } finally {
      busy = false; fields.disabled = completed; status.focus();
    }
  });
})();
