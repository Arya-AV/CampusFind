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

  // Confirmation dialog for marking an item as returned
  const markReturnedBtn = document.getElementById("mark-returned-button");
  const returnConfirmDialog = document.getElementById("return-confirm-dialog");
  const cancelReturnedBtn = document.getElementById("cancel-returned-button");
  const confirmReturnedBtn = document.getElementById("confirm-returned-button");
  const markReturnedForm = document.getElementById("mark-returned-form");

  if (markReturnedBtn && returnConfirmDialog) {
    const closeDialog = () => {
      if (typeof returnConfirmDialog.close === "function") {
        returnConfirmDialog.close();
      } else {
        returnConfirmDialog.removeAttribute("open");
      }
      markReturnedBtn.focus();
    };

    const openDialog = () => {
      if (typeof returnConfirmDialog.showModal === "function") {
        returnConfirmDialog.showModal();
      } else {
        returnConfirmDialog.setAttribute("open", "");
      }
      if (cancelReturnedBtn) {
        cancelReturnedBtn.focus();
      }
    };

    markReturnedBtn.addEventListener("click", openDialog);

    if (cancelReturnedBtn) {
      cancelReturnedBtn.addEventListener("click", (event) => {
        event.preventDefault();
        closeDialog();
      });
    }

    if (confirmReturnedBtn && markReturnedForm) {
      confirmReturnedBtn.addEventListener("click", (event) => {
        if (typeof markReturnedForm.requestSubmit === "function") {
          event.preventDefault();
          markReturnedForm.requestSubmit();
        }
      });
    }

    // Dismiss dialog when clicking on the backdrop
    returnConfirmDialog.addEventListener("click", (event) => {
      if (event.target === returnConfirmDialog) {
        closeDialog();
      }
    });

    // Native cancel event (e.g. Escape key in showModal)
    returnConfirmDialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      closeDialog();
    });

    // Keyboard Escape fallback
    returnConfirmDialog.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeDialog();
      }
    });
  }
});
