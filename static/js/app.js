document.addEventListener("DOMContentLoaded", () => {
  const search = document.querySelector('input[name="q"]');
  if (search) {
    search.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        search.value = "";
      }
    });
  }

  document.querySelectorAll(".flash").forEach((message) => {
    window.setTimeout(() => {
      message.classList.add("flash-hide");
    }, 5000);
  });

  const fileInput = document.querySelector('input[type="file"][name="image"]');
  if (fileInput) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      const hint = fileInput.parentElement.querySelector(".file-name");
      if (hint) hint.remove();
      if (file) {
        const label = document.createElement("small");
        label.className = "file-name";
        label.textContent = `Selected: ${file.name}`;
        fileInput.insertAdjacentElement("afterend", label);
      }
    });
  }
});

// Recently Viewed Items Tracking & Rendering
(function () {
  "use strict";

  var KEY   = "campusfind_recently_viewed";
  var MAX   = 6;
  var section = document.getElementById("recentlyViewedSection");
  var list    = document.getElementById("recentlyViewedList");

  function getIds() {
    try {
      var raw = localStorage.getItem(KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch (e) { return []; }
  }

  function saveIds(ids) {
    try { localStorage.setItem(KEY, JSON.stringify(ids.slice(0, MAX))); } catch (e) {}
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  window.CampusFind = window.CampusFind || {};
  window.CampusFind.recordViewed = function (itemId) {
    if (!itemId) return;
    var id = String(itemId);
    var ids = getIds().filter(function (x) { return x !== id; });
    ids.unshift(id);
    saveIds(ids);
  };

  async function fetchItem(id) {
    try {
      var r = await fetch("/api/items/" + encodeURIComponent(id), { headers: { Accept: "application/json" } });
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }

  async function render() {
    if (!section || !list) {
      section = document.getElementById("recentlyViewedSection");
      list    = document.getElementById("recentlyViewedList");
    }
    if (!section || !list) return;
    var ids = getIds();
    var ok = [];
    var stale = [];

    for (var i = 0; i < ids.length; i++) {
      var item = await fetchItem(ids[i]);
      if (item) ok.push(item); else stale.push(ids[i]);
    }

    if (stale.length) saveIds(ids.filter(function (x) { return stale.indexOf(x) === -1; }));

    if (!ok.length) {
      list.innerHTML = '<p class="recently-viewed__empty">You haven’t viewed any items yet.</p>';
      section.classList.remove("hidden");
      return;
    }

    list.innerHTML = ok.slice(0, MAX).map(function (item) {
      var img = item.image
        ? '<img src="' + escapeHtml(item.image) + '" alt="' + escapeHtml(item.title || "Item") + '">'
        : '<div class="placeholder-image">No Image</div>';
      return '<a class="recent-card" href="/items/' + encodeURIComponent(item.id) + '">' + img +
             '<span class="recent-card__title">' + escapeHtml(item.title || "Untitled item") + '</span></a>';
    }).join("");

    section.classList.remove("hidden");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var el = document.querySelector("[data-item-id]");
    if (el) {
      var id = el.getAttribute("data-item-id");
      if (id && window.CampusFind && typeof window.CampusFind.recordViewed === "function") {
        window.CampusFind.recordViewed(id);
      }
    }
    render();
  });
})();
