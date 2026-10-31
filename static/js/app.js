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

  // Live character counters for report form
  const initCharCounter = (inputSelector, counterSelector, maxLength) => {
    const field = document.querySelector(inputSelector);
    const counter = document.querySelector(counterSelector);

    if (field && counter) {
      const update = () => {
        const currentLength = field.value ? field.value.length : 0;
        counter.textContent = `${currentLength} / ${maxLength}`;
        if (currentLength >= maxLength) {
          counter.classList.add("limit-reached");
        } else {
          counter.classList.remove("limit-reached");
        }
      };

      field.addEventListener("input", update);
      field.addEventListener("keyup", update);
      field.addEventListener("change", update);
      update();
    }
  };

  initCharCounter('input[name="title"]', '#title-counter', 100);
  initCharCounter('textarea[name="description"]', '#description-counter', 1000);
});
