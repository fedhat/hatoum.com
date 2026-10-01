/* hatoum.com — small progressive enhancements. Everything works without JS;
   this adds the mobile menu, theme toggle, inline YouTube players, image
   lightbox, blog filter and the contact form. */
(function () {
  'use strict';

  var root = document.documentElement;

  function store(key, value) {
    try { value === undefined ? localStorage.removeItem(key) : localStorage.setItem(key, value); } catch (e) { /* private mode */ }
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    /* ---------------------------------------------------------- mobile nav */
    var toggle = document.querySelector('.nav-toggle');
    var nav = document.getElementById('site-nav');
    if (toggle && nav) {
      toggle.addEventListener('click', function () {
        var open = toggle.getAttribute('aria-expanded') !== 'true';
        toggle.setAttribute('aria-expanded', String(open));
        nav.classList.toggle('is-open', open);
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && nav.classList.contains('is-open')) {
          toggle.setAttribute('aria-expanded', 'false');
          nav.classList.remove('is-open');
          toggle.focus();
        }
      });
    }

    /* ---------------------------------------------------------- theme toggle */
    var themeBtn = document.querySelector('.theme-toggle');
    var media = window.matchMedia('(prefers-color-scheme: dark)');
    function currentTheme() {
      return root.getAttribute('data-theme') || (media.matches ? 'dark' : 'light');
    }
    function labelThemeButton() {
      if (themeBtn) themeBtn.setAttribute('aria-label', currentTheme() === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
    }
    if (themeBtn) {
      labelThemeButton();
      themeBtn.addEventListener('click', function () {
        var next = currentTheme() === 'dark' ? 'light' : 'dark';
        // Going back to the OS preference clears the override.
        if (next === (media.matches ? 'dark' : 'light')) {
          root.removeAttribute('data-theme');
          store('theme');
        } else {
          root.setAttribute('data-theme', next);
          store('theme', next);
        }
        labelThemeButton();
      });
      if (media.addEventListener) media.addEventListener('change', labelThemeButton);
    }

    /* ---------------------------------------------------------- YouTube facade */
    document.addEventListener('click', function (e) {
      var link = e.target.closest && e.target.closest('a.yt[data-yt]');
      if (!link || e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
      e.preventDefault();
      var params = 'autoplay=1&rel=0&playsinline=1';
      if (link.dataset.start) params += '&start=' + encodeURIComponent(link.dataset.start);
      var iframe = document.createElement('iframe');
      iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(link.dataset.yt) + '?' + params;
      iframe.title = link.dataset.title || 'YouTube video';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      iframe.allowFullscreen = true;
      iframe.referrerPolicy = 'strict-origin-when-cross-origin';
      var holder = document.createElement('div');
      holder.className = 'yt';
      if (link.style.aspectRatio) holder.style.aspectRatio = link.style.aspectRatio;
      holder.appendChild(iframe);
      link.replaceWith(holder);
      iframe.focus();
    });

    /* ---------------------------------------------------------- lightbox */
    var dialog;
    function openLightbox(href, caption) {
      if (!window.HTMLDialogElement) { window.location.href = href; return; }
      if (!dialog) {
        dialog = document.createElement('dialog');
        dialog.className = 'lightbox-dialog';
        dialog.innerHTML = '<button class="lightbox-close" type="button" aria-label="Close image">' +
          '<svg class="icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>' +
          '</button><img alt=""><p></p>';
        dialog.addEventListener('click', function (ev) {
          if (ev.target === dialog || ev.target.closest('.lightbox-close')) dialog.close();
        });
        document.body.appendChild(dialog);
      }
      var img = dialog.querySelector('img');
      img.src = href;
      img.alt = caption || '';
      dialog.querySelector('p').textContent = caption || '';
      dialog.showModal();
    }
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a.lightbox');
      if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      var img = a.querySelector('img');
      var fig = a.closest('figure');
      var cap = a.dataset.caption || (fig && fig.querySelector('figcaption') ? fig.querySelector('figcaption').textContent : '') || (img && img.alt) || '';
      openLightbox(a.href, cap.trim());
    });

    /* ---------------------------------------------------------- blog filter */
    var filter = document.getElementById('post-filter');
    if (filter) {
      var scope = document.querySelector('[data-filter-scope]');
      var rows = Array.prototype.slice.call(scope.querySelectorAll('.post-row'));
      var groups = Array.prototype.slice.call(scope.querySelectorAll('.year-group'));
      var empty = scope.querySelector('.empty-state');
      rows.forEach(function (r) { r._text = r.textContent.toLowerCase(); });
      filter.addEventListener('input', function () {
        var terms = filter.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
        var shown = 0;
        rows.forEach(function (r) {
          var hit = terms.every(function (t) { return r._text.indexOf(t) !== -1; });
          r.hidden = !hit;
          if (hit) shown++;
        });
        groups.forEach(function (g) { g.hidden = !g.querySelector('.post-row:not([hidden])'); });
        empty.hidden = shown !== 0;
      });
    }

    /* ---------------------------------------------------------- contact form */
    var form = document.getElementById('contact-form');
    if (form) {
      // Address is assembled here rather than written in the HTML to keep it away from scrapers.
      var address = form.dataset.user + '@' + form.dataset.domain;
      document.querySelectorAll('[data-email-link]').forEach(function (el) {
        el.href = 'mailto:' + address;
        el.textContent = address;
      });
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        if (!form.reportValidity()) return;
        var data = new FormData(form);
        var body = data.get('message') + '\n\n— ' + data.get('name') + ' <' + data.get('email') + '>';
        var url = 'mailto:' + address +
          '?subject=' + encodeURIComponent(data.get('subject')) +
          '&body=' + encodeURIComponent(body);
        window.location.href = url;
        var status = document.getElementById('form-status');
        status.textContent = 'Your email app should open with the message ready to send. ' +
          'If nothing happens, email ' + address + ' directly. / ¡Gracias!';
      });
    }
  });
})();
