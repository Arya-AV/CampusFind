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

  setUpRecentlyViewed();
});

// Recently viewed items. Only item IDs are stored, in this browser's
// localStorage, newest first. The homepage asks the server for the matching
// cards, so titles and images are always current and deleted items drop out.
function setUpRecentlyViewed() {
  const STORAGE_KEY = "campusfind:recently-viewed";
  const limit = Number(document.body.dataset.recentlyViewedLimit) || 6;

  const readIds = () => {
    try {
      const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "[]");
      if (!Array.isArray(saved)) return [];
      const ids = saved.filter((id) => Number.isInteger(id) && id > 0);
      return [...new Set(ids)].slice(0, limit);
    } catch (error) {
      return [];
    }
  };

  const saveIds = (ids) => {
    try {
      if (ids.length) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch (error) {
      // Storage can be blocked or full (for example in private browsing). History is optional.
    }
  };

  // Item detail page: move this item to the front of the history.
  const viewedItem = document.querySelector("[data-record-view]");
  if (viewedItem) {
    const id = Number(viewedItem.dataset.recordView);
    if (Number.isInteger(id) && id > 0) {
      saveIds([id, ...readIds().filter((savedId) => savedId !== id)].slice(0, limit));
    }
  }

  // Homepage: show the history.
  const section = document.querySelector("[data-recently-viewed]");
  if (!section) return;
  const list = section.querySelector("[data-recently-viewed-list]");
  const emptyMessage = section.querySelector("[data-recently-viewed-empty]");
  const clearButton = section.querySelector("[data-recently-viewed-clear]");

  // Puts the server-rendered cards in place and returns the IDs that were shown.
  const showCards = (html) => {
    list.innerHTML = html;
    const shownIds = Array.from(list.querySelectorAll("[data-item-id]"), (card) => Number(card.dataset.itemId));
    if (!shownIds.length) list.innerHTML = "";
    emptyMessage.hidden = shownIds.length > 0;
    clearButton.hidden = shownIds.length === 0;
    section.hidden = false;
    return shownIds;
  };

  clearButton.addEventListener("click", () => {
    saveIds([]);
    showCards("");
  });

  const ids = readIds();
  if (!ids.length) {
    // Also clears any unreadable value left in storage.
    saveIds(showCards(""));
    return;
  }

  fetch(`${section.dataset.url}?ids=${ids.join(",")}`, { headers: { Accept: "text/html" } })
    .then((response) => {
      if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
      return response.text();
    })
    .then((html) => {
      // Forget items that no longer exist, keeping the order of the rest.
      saveIds(showCards(html));
    })
    .catch(() => {
      // Leave the section hidden and keep the saved history for next time.
    });
}
