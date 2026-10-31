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

  // Copy contact email functionality
  document.querySelectorAll(".copy-email-btn").forEach((button) => {
    let resetTimer = null;

    button.addEventListener("click", async () => {
      const email = button.getAttribute("data-email") || "";
      if (!email) return;

      const iconSpan = button.querySelector(".copy-icon");
      const textSpan = button.querySelector(".copy-text");
      const originalText = textSpan ? textSpan.textContent : button.textContent;
      const originalIcon = iconSpan ? iconSpan.textContent : "";

      const setFeedback = (icon, text, className) => {
        if (iconSpan) iconSpan.textContent = icon;
        if (textSpan) textSpan.textContent = text;
        button.classList.add(className);

        if (resetTimer) clearTimeout(resetTimer);
        resetTimer = setTimeout(() => {
          if (iconSpan) iconSpan.textContent = originalIcon;
          if (textSpan) textSpan.textContent = originalText;
          button.classList.remove(className);
        }, 2000);
      };

      const copyWithFallback = (text) => {
        try {
          const textarea = document.createElement("textarea");
          textarea.value = text;
          textarea.setAttribute("readonly", "");
          textarea.style.position = "absolute";
          textarea.style.left = "-9999px";
          textarea.style.fontSize = "12pt";
          document.body.appendChild(textarea);
          textarea.select();
          const successful = document.execCommand("copy");
          document.body.removeChild(textarea);
          return successful;
        } catch (err) {
          return false;
        }
      };

      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(email);
          setFeedback("✓", "Copied!", "copied");
        } else if (copyWithFallback(email)) {
          setFeedback("✓", "Copied!", "copied");
        } else {
          setFeedback("✕", "Failed to copy", "copy-error");
        }
      } catch (err) {
        if (copyWithFallback(email)) {
          setFeedback("✓", "Copied!", "copied");
        } else {
          setFeedback("✕", "Failed to copy", "copy-error");
        }
      }
    });
  });
});
