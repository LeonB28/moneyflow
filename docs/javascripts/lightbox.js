/**
 * Simple image lightbox for documentation screenshots
 * Works on all screen sizes (desktop, tablet, mobile)
 */

(function() {
  'use strict';

  // Create lightbox elements
  function createLightbox() {
    const overlay = document.createElement('div');
    overlay.id = 'lightbox-overlay';
    overlay.innerHTML = `
      <div class="lightbox-content">
        <img id="lightbox-image" src="" alt="">
        <button id="lightbox-close" aria-label="Close lightbox">&times;</button>
        <div class="lightbox-caption"></div>
      </div>
    `;
    document.body.appendChild(overlay);

    // Close on overlay click (not on image or caption)
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay || e.target.id === 'lightbox-close') {
        closeLightbox();
      }
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.classList.contains('active')) {
        closeLightbox();
      }
    });

    // Support touch gestures for mobile
    let touchStartY = 0;
    overlay.addEventListener('touchstart', (e) => {
      touchStartY = e.touches[0].clientY;
    });

    overlay.addEventListener('touchend', (e) => {
      const touchEndY = e.changedTouches[0].clientY;
      const swipeDistance = touchStartY - touchEndY;

      // Swipe down to close (must swipe at least 100px)
      if (swipeDistance < -100) {
        closeLightbox();
      }
    });

    return overlay;
  }

  // Open lightbox with image
  function openLightbox(imgSrc, altText) {
    const overlay = document.getElementById('lightbox-overlay') || createLightbox();
    const lightboxImg = document.getElementById('lightbox-image');
    const caption = overlay.querySelector('.lightbox-caption');

    lightboxImg.src = imgSrc;
    lightboxImg.alt = altText;
    caption.textContent = altText;

    overlay.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent scrolling
  }

  // Close lightbox
  function closeLightbox() {
    const overlay = document.getElementById('lightbox-overlay');
    if (overlay) {
      overlay.classList.remove('active');
      document.body.style.overflow = ''; // Restore scrolling
    }
  }

  // Make images clickable
  function initLightbox() {
    // Target all content images (screenshots)
    const images = document.querySelectorAll('.md-content img');

    images.forEach(img => {
      // Skip if already processed
      if (img.classList.contains('lightbox-enabled')) return;

      // Add class and click handler
      img.classList.add('lightbox-enabled');
      img.title = img.alt + ' (click to enlarge)';

      img.addEventListener('click', (e) => {
        e.preventDefault();
        openLightbox(img.src, img.alt);
      });
    });
  }

  // Initialize on page load
  document.addEventListener('DOMContentLoaded', initLightbox);

  // Re-initialize on Material for MkDocs instant navigation
  if (typeof document$ !== 'undefined') {
    document$.subscribe(() => {
      initLightbox();
    });
  }
})();
