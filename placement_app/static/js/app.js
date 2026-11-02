const toggle = document.querySelector('.mobile-toggle');
const sidebar = document.getElementById('sidebar');
const mobileNav = window.matchMedia('(max-width: 760px)');
function setNavigation(open, focus = false) {
  open = mobileNav.matches && open;
  document.body.classList.toggle('nav-open', open);
  toggle?.setAttribute('aria-expanded', String(open));
  if (sidebar) sidebar.inert = mobileNav.matches && !open;
  if (focus) {
    if (open) sidebar?.querySelector('a')?.focus();
    else toggle?.focus();
  }
}
setNavigation(false);
mobileNav.addEventListener('change', () => setNavigation(false));
toggle?.addEventListener('click', () => setNavigation(!document.body.classList.contains('nav-open'), true));
document.addEventListener('keydown', e => {
  if (!document.body.classList.contains('nav-open')) return;
  if (e.key === 'Escape') { setNavigation(false, true); return; }
  if (e.key === 'Tab') {
    const items = [...sidebar.querySelectorAll('a[href],button:not([disabled])'), toggle];
    const index = items.indexOf(document.activeElement);
    if (e.shiftKey && index <= 0) { e.preventDefault(); items.at(-1).focus(); }
    else if (!e.shiftKey && (index < 0 || index === items.length - 1)) { e.preventDefault(); items[0].focus(); }
  }
});
document.querySelectorAll('.dismiss').forEach(b => b.addEventListener('click', () => b.closest('.notice').remove()));
document.querySelectorAll('[data-demo-email]').forEach(b => b.addEventListener('click', () => {
  document.querySelector('[name=username]').value = b.dataset.demoEmail;
  document.querySelector('[name=password]').value = 'Campus@2027!';
  document.querySelector('[name=password]').focus();
}));
const dialog = document.getElementById('confirm-dialog');
let pendingForm = null;
document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', e => {
  if (form.dataset.confirmed === 'yes') return;
  e.preventDefault(); pendingForm = form;
  document.getElementById('confirm-message').textContent = form.dataset.confirm;
  dialog.showModal();
}));
dialog?.addEventListener('close', () => {
  if (dialog.returnValue === 'confirm' && pendingForm) {
    pendingForm.dataset.confirmed = 'yes'; pendingForm.requestSubmit();
  }
  pendingForm = null;
});
const role = document.querySelector('select[name=role]');
function updateRegistration() {
  const student = role.value === 'student';
  ['roll_no', 'branch', 'cgpa', 'graduation_year'].forEach(name => {
    const wrapper = document.querySelector(`[data-field="${name}"]`);
    if (!wrapper) return;
    wrapper.hidden = !student;
    const input = wrapper.querySelector('input,select');
    input.required = student;
    input.disabled = !student;
  });
  const website = document.querySelector('[data-field=website]');
  if (website) { website.hidden = student; website.querySelector('input').disabled = student; }
}
if (role) { role.addEventListener('change', updateRegistration); updateRegistration(); }
// Make field errors available to screen readers, alongside Django's help text.
document.querySelectorAll('.has-error').forEach(wrapper => {
  const input = wrapper.querySelector('input,textarea,select');
  const error = wrapper.querySelector('.field-error');
  if (input && error) {
    error.id = `${input.id}-error`;
    input.setAttribute('aria-invalid', 'true');
    input.setAttribute('aria-describedby', [input.getAttribute('aria-describedby'), error.id].filter(Boolean).join(' '));
  }
});
document.querySelector('.app-shell')?.addEventListener('click', e => {
  if (document.body.classList.contains('nav-open') && !e.target.closest('.mobile-toggle')) {
    setNavigation(false, true);
  }
});
