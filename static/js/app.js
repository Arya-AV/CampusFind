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

  const returnForm = document.querySelector(".return-form");
  const returnConfirmation = document.querySelector(".return-confirmation");
  if (returnForm && returnConfirmation) {
    let confirmed = false;
    const submitButton = returnForm.querySelector('button[type="submit"]');

    returnForm.addEventListener("submit", (event) => {
      if (confirmed) {
        confirmed = false;
        return;
      }

      event.preventDefault();
      returnConfirmation.showModal();
    });

    returnConfirmation.addEventListener("cancel", (event) => {
      event.preventDefault();
      returnConfirmation.close("cancel");
    });

    returnConfirmation.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        returnConfirmation.close("cancel");
      }
    });

    returnConfirmation.addEventListener("close", () => {
      if (returnConfirmation.returnValue !== "confirm") {
        submitButton.focus();
        return;
      }

      confirmed = true;
      returnForm.requestSubmit(submitButton);
    });
  }
});
