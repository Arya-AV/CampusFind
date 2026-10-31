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
    document.querySelectorAll(".copy-email").forEach((button) => {
    const status = button.closest(".detail-info").querySelector(".copy-status");
    const originalText = button.textContent;
    let timer;

    const showFeedback = (message, isError) => {
      status.textContent = message;
      status.classList.toggle("copy-error", isError);
      button.textContent = isError ? originalText : "Copied ✓";
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        button.textContent = originalText;
        status.textContent = "";
        status.classList.remove("copy-error");
      }, 3000);
    };

    
      const legacyCopy = (text) => {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      document.body.removeChild(area);
      return ok;
    };

    button.addEventListener("click", async () => {
      const email = button.dataset.email;
      try {
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
          throw new Error("Clipboard API unavailable");
        }
        await navigator.clipboard.writeText(email);
        showFeedback("Email address copied to clipboard.", false);
      } catch (err) {
        if (legacyCopy(email)) {
          showFeedback("Email address copied to clipboard.", false);
        } else {
          const link = button.closest(".detail-info").querySelector(".email-row a");
          const range = document.createRange();
          range.selectNodeContents(link);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          showFeedback("Couldn't copy automatically. The address is selected, so press Ctrl+C (Cmd+C on Mac).", true);
        }
      }
    });
  });
});
