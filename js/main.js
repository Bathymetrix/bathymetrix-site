document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('[data-nav-toggle]');
  const nav = document.querySelector('[data-nav]');

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(isOpen));
    });

    nav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        nav.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  const form = document.querySelector('[data-mailto-form]');
  if (form) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const name = (data.get('name') || '').toString().trim();
      const email = (data.get('email') || '').toString().trim();
      const organization = (data.get('organization') || '').toString().trim();
      const message = (data.get('message') || '').toString().trim();

      const subject = `Bathymetrix inquiry${name ? ` — ${name}` : ''}`;
      const lines = [
        name ? `Name: ${name}` : '',
        email ? `Email: ${email}` : '',
        organization ? `Organization: ${organization}` : '',
        '',
        message || '(No message provided)'
      ].filter(Boolean);

      const body = encodeURIComponent(lines.join('\n'));
      const href = `mailto:info@bathymetrix.com?subject=${encodeURIComponent(subject)}&body=${body}`;
      window.location.href = href;
    });
  }
});
