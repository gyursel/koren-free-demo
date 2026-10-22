/* Progressive enhancement: usable HTML and the original SVG remain the default. */
(() => {
  const header = document.querySelector('.site-header');
  if (!header) return;
  const updateHeader = () => document.documentElement.style.setProperty('--header-height', `${Math.ceil(header.getBoundingClientRect().height)}px`);
  updateHeader();
  if ('ResizeObserver' in window) new ResizeObserver(updateHeader).observe(header);
  const desktop = window.matchMedia('(min-width: 781px)');
  desktop.addEventListener('change', () => { if (desktop.matches) closeMobileNav(); });
  document.querySelectorAll('.story-skip, .skip-link').forEach(link => link.addEventListener('click', () => {
    document.querySelector('#products').focus({preventScroll:true});
  }));
})();
