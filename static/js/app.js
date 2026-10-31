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

  const inputsWithCounter = document.querySelectorAll("input[maxlength], textarea[maxlength]");
  inputsWithCounter.forEach((input) => {
    const max = input.getAttribute("maxlength");
    if (!max) return;
    const counter = document.getElementById(`${input.name}-counter`);
    if (counter) {
      const update = () => {
        counter.textContent = `${input.value.length} / ${max}`;
      };
      input.addEventListener("input", update);
      update();
    }
  });
      }
    });
  }
});
