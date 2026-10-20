(() => {
  const form = document.querySelector('#appointment-form');
  if (!form) return;
  const fields = form.querySelector('fieldset');
  const status = document.querySelector('#appointment-status');
  const button = form.querySelector('[type="submit"]');
  const successDialog = document.querySelector('#appointment-success');
  document.querySelector('#appointment-success-close').addEventListener('click', () => window.location.reload());
  successDialog.addEventListener('close', () => status.focus());
  let busy = false;
  let currentStep = 0;
  const steps = [...form.querySelectorAll('[data-booking-step]')];
  form.noValidate = true;
  function showStep(index, focus = true) {
    currentStep = index;
    steps.forEach((step, i) => { step.hidden = i !== index; });
    form.querySelectorAll('[data-step-indicator]').forEach((indicator, i) => {
      indicator.classList.toggle('is-complete', i < index);
      if (i === index) indicator.setAttribute('aria-current', 'step');
      else indicator.removeAttribute('aria-current');
    });
    if (focus) steps[index].querySelector('h3').focus();
  }
  function validateStep(index) {
    const invalid = [...steps[index].querySelectorAll('input, select, textarea')].find(input => !input.checkValidity());
    if (!invalid) return true;
    showStep(index, false);
    invalid.reportValidity();
    invalid.focus();
    return false;
  }
  document.querySelector('#appointment-next').addEventListener('click', () => {
    if (!fields.disabled && !busy && validateStep(0)) showStep(1);
  });
  document.querySelector('#appointment-previous').addEventListener('click', () => {
    if (!busy) showStep(0);
  });
  form.addEventListener('reset', () => showStep(0, false));
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
  let bookingHours = null, doctorSchedules = {};
  const timeField = form.elements.appointment_time;
  const dateField = form.elements.appointment_date;
  const doctorField = form.elements.doctor_name;
  const scheduleNote = timeField.parentElement.querySelector('small') || document.createElement('small');
  scheduleNote.id = 'booking-schedule-note';scheduleNote.setAttribute('aria-live','polite');
  timeField.parentElement.append(scheduleNote);
  timeField.setAttribute('aria-describedby','booking-schedule-note');
  function timeLabel(value){const [h,m]=value.split(':').map(Number);return `${h%12||12}:${String(m).padStart(2,'0')} ${h>=12?'PM':'AM'}`;}
  function updateBookingHours(){
    if(!bookingHours)return;
    timeField.min=bookingHours.start;timeField.max=bookingHours.end;timeField.setCustomValidity('');
    const schedule=doctorSchedules[doctorField.value];
    if(schedule && dateField.value){
      const day=new Date(dateField.value+'T12:00:00Z').toLocaleDateString('en-US',{weekday:'long',timeZone:'Asia/Dhaka'}).toLowerCase();
      const slots=schedule.filter(s=>s.day===day);
      scheduleNote.textContent=slots.length?'Doctor’s available times: '+slots.map(s=>timeLabel(s.start)+' – '+timeLabel(s.end)).join(' · ')+' (Bangladesh time)':'This doctor has no published availability on this day. Please choose another date or doctor.';
      if(!slots.length || (timeField.value && !slots.some(s=>s.start<=timeField.value&&timeField.value<s.end)))timeField.setCustomValidity('Choose a time within this doctor’s availability for the selected day.');
    }else{
      scheduleNote.textContent='Appointment hours: '+bookingHours.label+' · Bangladesh time';
      if(schedule)scheduleNote.textContent+=' · Choose a date to see this doctor’s available times.';
    }
  }
  for(const field of [timeField,dateField,doctorField])field.addEventListener('input',updateBookingHours);
  doctorField.addEventListener('change',updateBookingHours);
  fetch(form.dataset.endpoint, {credentials: 'same-origin', cache: 'no-store'})
    .then(readResponse).then(data => {
      for (const [name, options] of Object.entries(data.options)) {
        const select = form.elements.namedItem(name);
        for (const [value, label] of options) select.add(new Option(label, value));
      }
      bookingHours=data.hours;doctorSchedules=data.doctor_schedules||{};
      document.querySelectorAll('[data-appointment-hours], .appointment-hours strong').forEach(node=>{node.textContent=bookingHours.label;});
      updateBookingHours();
      styleBranchDropdown();
      form.elements.appointment_date.min = data.today;
      fields.disabled = false;
      message('Choose your preferred date and time. Fields marked * are required.');
    }).catch(() => message('Online booking is temporarily unavailable. Please open the booking portal below or call the clinic.', true));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || fields.disabled) return;
    if (currentStep === 0) {
      if (validateStep(0)) showStep(1);
      return;
    }
    if (!validateStep(0) || !validateStep(1)) return;
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
      document.querySelector('#appointment-success-message').textContent = data.message || 'Your appointment request has been received. The clinic will confirm your visit.';
      successDialog.showModal();
    } catch (error) {
      // A lost response can follow a saved booking. Never retry automatically.
      const uncertain = !error.data || error.data.uncertain;
      completed = Boolean(uncertain);
      message(error.data?.error || 'We could not confirm the booking result. Please call the clinic before submitting again to avoid a duplicate.', true);
      let errorStep = null;
      for (const [name, errors] of Object.entries(error.data?.errors || {})) {
        const input = form.elements.namedItem(name);
        if (!input) continue;
        if (errorStep === null) errorStep = steps.indexOf(input.closest('[data-booking-step]'));
        const node = document.createElement('p');
        node.id = `${input.id}-error`; node.className = 'booking-error';
        node.textContent = errors.join(' '); input.after(node);
        input.setAttribute('aria-invalid', 'true'); input.setAttribute('aria-describedby', name === 'chamber_address' ? `booking-branch-address ${node.id}` : node.id);

      }
      if (errorStep !== null && errorStep >= 0) showStep(errorStep, false);
      button.textContent = uncertain ? 'Please contact the clinic' : 'Request appointment →';
    } finally {
      busy = false; fields.disabled = completed; if (!successDialog.open) status.focus();
    }
  });
})();
