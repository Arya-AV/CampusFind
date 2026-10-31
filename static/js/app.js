document.addEventListener("DOMContentLoaded", () => {
  const search = document.querySelector('input[name="q"]');
  if (search) {
    search.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        search.value = "";
        const form = search.form;
        if (form) {
          if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
          } else {
            form.submit();
          }
        }
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

  document.querySelectorAll(".copy-email-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const email = btn.dataset.email;
      if (!email) return;

      const setFeedback = (text, className) => {
        const originalText = btn.dataset.originalText || btn.textContent;
        btn.dataset.originalText = originalText;
        btn.textContent = text;
        if (className) btn.classList.add(className);
        btn.disabled = true;

        setTimeout(() => {
          btn.textContent = originalText;
          if (className) btn.classList.remove(className);
          btn.disabled = false;
        }, 2000);
      };

      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(email);
        } else {
          const textArea = document.createElement("textarea");
          textArea.value = email;
          textArea.style.position = "fixed";
          textArea.style.left = "-9999px";
          textArea.style.top = "0";

          document.body.appendChild(textArea);

          try {
            textArea.focus();
            textArea.select();

            const successful = document.execCommand("copy");

            if (!successful) {
              throw new Error("Copy command failed");
            }
          } finally {
            textArea.remove();
          }
        }
        setFeedback("Copied!", "copied");
      } catch (err) {
        setFeedback("Failed to copy", "failed");
      }
    });
  });
});
