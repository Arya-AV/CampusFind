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

  const detailContainer = document.querySelector(".detail-page[data-item-id]");
  if (detailContainer) {
    const id = detailContainer.getAttribute("data-item-id");
    const title = detailContainer.getAttribute("data-item-title");
    const category = detailContainer.getAttribute("data-item-category");
    const status = detailContainer.getAttribute("data-item-status");
    const image = detailContainer.getAttribute("data-item-image");
    if (id && title) {
      try {
        let recents = JSON.parse(localStorage.getItem("campusfind_recently_viewed") || "[]");
        recents = recents.filter((item) => String(item.id) !== String(id));
        recents.unshift({ id, title, category, status, image });
        if (recents.length > 5) recents = recents.slice(0, 5);
        localStorage.setItem("campusfind_recently_viewed", JSON.stringify(recents));
      } catch (e) {}
    }
  }

  const recentList = document.getElementById("recently-viewed-list");
  const recentSection = document.getElementById("recently-viewed-section");
  if (recentList && recentSection) {
    try {
      const recents = JSON.parse(localStorage.getItem("campusfind_recently_viewed") || "[]");
      if (recents.length > 0) {
        recentList.innerHTML = recents
          .map(
            (item) => `
          <a class="recent-item-card" href="/item/${item.id}">
            <div class="recent-item-info">
              <span class="status-pill status-${(item.status || "").toLowerCase()}">${item.status}</span>
              <strong>${item.title}</strong>
              <small>${item.category}</small>
            </div>
          </a>`
          )
          .join("");
        recentSection.style.display = "block";
      }
    } catch (e) {}
  }
      }
    });
  }
});
