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

  const returnForm = document.querySelector("#mark-returned-form");
  const returnDialog = document.querySelector("#return-confirmation");
  const confirmReturn = document.querySelector("#confirm-return");
  const cancelReturn = document.querySelector("#cancel-return");

  if (returnForm && returnDialog && confirmReturn && cancelReturn) {
    let confirmedReturn = false;
    returnForm.addEventListener("submit", (event) => {
      if (confirmedReturn) {
        confirmedReturn = false;
        return;
      }
      event.preventDefault();
      returnDialog.showModal();
    });

    cancelReturn.addEventListener("click", () => returnDialog.close());
    confirmReturn.addEventListener("click", () => {
      confirmedReturn = true;
      returnDialog.close();
      returnForm.requestSubmit();
    });
  }
});
