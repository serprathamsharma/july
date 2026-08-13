document.addEventListener('DOMContentLoaded', () => {
  // Mobile Hamburger Menu Elements
  const burgerBtn = document.querySelector('.burger-btn');
  const mobileOverlay = document.getElementById('mobile-overlay');
  const mobileMenu = document.getElementById('mobile-menu');
  const mobileNavLinks = document.querySelectorAll('.mobile-nav-link, .mobile-signin-btn');

  function openMenu() {
    if (!burgerBtn || !mobileOverlay || !mobileMenu) return;
    burgerBtn.classList.add('open');
    burgerBtn.setAttribute('aria-expanded', 'true');
    mobileOverlay.hidden = false;
    mobileMenu.hidden = false;
    document.body.style.overflow = 'hidden';
  }

  function closeMenu() {
    if (!burgerBtn || !mobileOverlay || !mobileMenu) return;
    burgerBtn.classList.remove('open');
    burgerBtn.setAttribute('aria-expanded', 'false');
    mobileOverlay.hidden = true;
    mobileMenu.hidden = true;
    document.body.style.overflow = '';
  }

  if (burgerBtn) {
    burgerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = burgerBtn.classList.contains('open');
      if (isOpen) {
        closeMenu();
      } else {
        openMenu();
      }
    });
  }

  if (mobileOverlay) {
    mobileOverlay.addEventListener('click', closeMenu);
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMenu();
    }
  });

  mobileNavLinks.forEach((link) => {
    link.addEventListener('click', closeMenu);
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 720) {
      closeMenu();
    }
  });

  // Count-up Animation for Stats Footer
  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

  const animateStatValue = (card, index) => {
    const targetVal = parseFloat(card.dataset.target);
    const suffix = card.dataset.suffix || '';
    const decimals = parseInt(card.dataset.decimals || '0', 10);
    const valueContainer = card.querySelector('.stat-value');

    if (!valueContainer || isNaN(targetVal)) return;

    const duration = 1500 + index * 80;
    const startOffset = 480 + index * 90;

    setTimeout(() => {
      const startTime = performance.now();

      const updateValue = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = easeOutCubic(progress);
        const currentVal = targetVal * easedProgress;

        valueContainer.innerHTML = `${currentVal.toFixed(decimals)}<span class="stat-suffix">${suffix}</span>`;

        if (progress < 1) {
          requestAnimationFrame(updateValue);
        } else {
          valueContainer.innerHTML = `${targetVal.toFixed(decimals)}<span class="stat-suffix">${suffix}</span>`;
        }
      };

      requestAnimationFrame(updateValue);
    }, startOffset);
  };

  const statsObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const statCards = entry.target.querySelectorAll('.stat-card');
        statCards.forEach((card, idx) => animateStatValue(card, idx));
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.25 });

  const statsFooter = document.querySelector('.stats-footer');
  if (statsFooter) {
    statsObserver.observe(statsFooter);
  }
});
