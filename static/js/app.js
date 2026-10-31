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

  const copyBtn = document.querySelector(".copy-email-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const email = copyBtn.getAttribute("data-email");
      if (!email) return;
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(email);
        } else {
          const textarea = document.createElement("textarea");
          textarea.value = email;
          textarea.style.position = "fixed";
          textarea.style.opacity = "0";
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand("copy");
          textarea.remove();
        }
        const originalText = copyBtn.textContent;
        copyBtn.textContent = "Copied!";
        copyBtn.classList.add("copied");
        setTimeout(() => {
          copyBtn.textContent = originalText;
          copyBtn.classList.remove("copied");
        }, 2000);
      } catch (err) {
        copyBtn.textContent = "Failed to copy";
        setTimeout(() => {
          copyBtn.textContent = "Copy";
        }, 2000);
      }
    });
  }
});
