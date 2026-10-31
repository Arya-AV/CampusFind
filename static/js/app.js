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
    const preview = fileInput.parentElement.querySelector(".image-preview");
    const previewImage = preview && preview.querySelector("img");
    let previewUrl = null;
    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      const hint = fileInput.parentElement.querySelector(".file-name");
      if (hint) hint.remove();
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
      if (previewImage) previewImage.removeAttribute("src");
      if (preview) preview.hidden = true;
      if (file) {
        const label = document.createElement("small");
        label.className = "file-name";
        label.textContent = `Selected: ${file.name}`;
        fileInput.insertAdjacentElement("afterend", label);
        if (previewImage && file.type.startsWith("image/")) {
          previewUrl = URL.createObjectURL(file);
          previewImage.src = previewUrl;
          preview.hidden = false;
        }
      }
    });
    const form = fileInput.form;
    if (form && preview) {
      form.addEventListener("reset", () => {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = null;
        preview.hidden = true;
        if (previewImage) previewImage.removeAttribute("src");
        const hint = fileInput.parentElement.querySelector(".file-name");
        if (hint) hint.remove();
      });
    }
  }
});
