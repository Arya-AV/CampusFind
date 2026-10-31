document.addEventListener("DOMContentLoaded", () => {
  // --- EXISTING CODE ---
  const search = document.querySelector('input[name="q"]');
  if (search) {
    search.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault(); // Prevent default browser escape behavior
        search.value = ""; // Clear the search text
        search.closest("form").submit(); // Automatically submit the form to refresh results
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

  // --- NEW RECENTLY VIEWED LOGIC ---
  const RECENT_KEY = "campusfind_recent_items";
  const MAX_ITEMS = 5;

  // 1. RECORD ITEM ON DETAIL PAGE
  const meta = document.getElementById("item-metadata");
  if (meta) {
    try {
      const id = meta.getAttribute("data-id");
      const title = meta.getAttribute("data-title");
      const image = meta.getAttribute("data-image");

      let recent = JSON.parse(localStorage.getItem(RECENT_KEY)) || [];

      // Avoid duplicate entries: remove if it already exists in the array
      recent = recent.filter(item => item.id !== id);

      // Add current item to the beginning of the array
      recent.unshift({ id, title, image });

      // Enforce the 5-item limit
      if (recent.length > MAX_ITEMS) {
        recent = recent.slice(0, MAX_ITEMS);
      }

      localStorage.setItem(RECENT_KEY, JSON.stringify(recent));
    } catch (error) {
      console.error("Error saving recent item:", error);
    }
  }

  // 2. DISPLAY ITEMS ON HOMEPAGE
  const recentContainer = document.getElementById("recently-viewed-container");
  if (recentContainer) {
    try {
      const recent = JSON.parse(localStorage.getItem(RECENT_KEY)) || [];

      if (recent.length === 0) {
        recentContainer.innerHTML = '<p class="empty-state">No viewing history yet. Start exploring!</p>';
      } else {
        recentContainer.innerHTML = recent.map(item => {
          // Display the actual image, or a themed placeholder box if it equals "none"
          const imgHTML = item.image !== 'none'
            ? `<img src="${item.image}" alt="${item.title}">`
            : `<div style="height: 120px; background: #e9ecef; display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #adb5bd; border-bottom: 1px solid #eee;">✦</div>`;

          return `
            <div class="recent-card">
              <a href="/item/${item.id}">
                ${imgHTML}
                <h4>${item.title}</h4>
              </a>
            </div>
          `;
        }).join("");
      }
    } catch (error) {
      console.error("Error loading recent items:", error);
      recentContainer.innerHTML = '<p class="empty-state">Unable to load history.</p>';
      localStorage.removeItem(RECENT_KEY);
    }
  }
});