/* Expanse site: theme toggle, mobile nav, copy buttons, scroll reveal, TOC highlight.
   Vanilla JS, no dependencies. The theme is applied early by an inline script in
   <head> so the page never flashes; this file only wires the toggle. */
(function () {
  "use strict";
  var root = document.documentElement;
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function currentTheme() {
    var set = root.getAttribute("data-theme");
    if (set) return set;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  // Theme toggle: flips between light and dark, remembered per browser.
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("expanse-theme", next); } catch (e) { /* storage blocked */ }
      btn.setAttribute("aria-label", "Switch to " + (next === "dark" ? "light" : "dark") + " theme");
    });
  });

  // Mobile navigation drawer.
  var menuBtn = document.querySelector("[data-nav-toggle]");
  var nav = document.querySelector("[data-nav]");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("open")) {
        nav.classList.remove("open");
        menuBtn.setAttribute("aria-expanded", "false");
        menuBtn.focus();
      }
    });
  }

  // Copy buttons on every code block and terminal.
  function copyFallback(text) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok ? Promise.resolve() : Promise.reject(new Error("copy unavailable"));
  }
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () { return copyFallback(text); });
    }
    return copyFallback(text);
  }
  document.querySelectorAll(".code, .terminal").forEach(function (block) {
    var pre = block.querySelector("pre");
    if (!pre) return;
    var btn = document.createElement("button");
    btn.type = "button"; btn.className = "copy-btn"; btn.setAttribute("aria-label", "Copy to clipboard");
    btn.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-copy"/></svg><span>Copy</span>';
    btn.addEventListener("click", function () {
      // Copy commands only: drop prompt markers and program output lines.
      var lines = [];
      pre.querySelectorAll(".cmd").forEach(function (el) { lines.push(el.textContent); });
      var text = lines.length ? lines.join("\n") : pre.textContent;
      copyText(text.trim()).then(function () { flash("Copied"); }, function () { flash("Select to copy"); });
      function flash(label) {
        btn.classList.add("done"); btn.querySelector("span").textContent = label;
        setTimeout(function () { btn.classList.remove("done"); btn.querySelector("span").textContent = "Copy"; }, 1600);
      }
    });
    block.appendChild(btn);
  });

  // Reveal-on-scroll, skipped entirely when the user prefers reduced motion.
  var revealed = document.querySelectorAll(".reveal");
  if (revealed.length && !reduced && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.05 });
    revealed.forEach(function (el) { io.observe(el); });
  } else {
    revealed.forEach(function (el) { el.classList.add("in"); });
  }

  // Table of contents: highlight the last section heading scrolled past the header.
  var toc = document.querySelector(".toc");
  if (toc) {
    var links = Array.prototype.slice.call(toc.querySelectorAll("a[href^='#']"));
    var targets = links.map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); }).filter(Boolean);
    var active = null, ticking = false;
    var update = function () {
      ticking = false;
      var line = 96, current = targets[0];
      targets.forEach(function (t) { if (t.getBoundingClientRect().top <= line) current = t; });
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) current = targets[targets.length - 1];
      if (!current || current.id === active) return;
      active = current.id;
      links.forEach(function (a) { a.classList.toggle("active", a.getAttribute("href") === "#" + active); });
    };
    var onScroll = function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
  }
})();
