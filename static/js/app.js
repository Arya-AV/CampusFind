document.addEventListener("DOMContentLoaded", () => {
  // Clear search on Escape
  const search = document.querySelector('input[name="q"]');
  if (search) {
    search.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        search.value = "";
      }
    });
  }

  // Auto-hide flash messages
  document.querySelectorAll(".flash").forEach((message) => {
    window.setTimeout(() => {
      message.classList.add("flash-hide");
    }, 5000);
  });

  // File upload indicator
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

  // Authentication Modal logic
  const authModal = document.getElementById("authModal");
  if (authModal) {
    const closeBtn = document.getElementById("closeAuthModal");
    const tabLoginBtn = document.getElementById("tabLoginBtn");
    const tabSignupBtn = document.getElementById("tabSignupBtn");
    const loginTab = document.getElementById("loginTab");
    const signupTab = document.getElementById("signupTab");
    const switchToSignup = document.getElementById("switchToSignup");
    const switchToLogin = document.getElementById("switchToLogin");
    const modalAlert = document.getElementById("modalAlert");
    const loginForm = document.getElementById("loginForm");
    const signupForm = document.getElementById("signupForm");

    function showAlert(text, type = "error") {
      if (!modalAlert) return;
      modalAlert.className = `modal-alert ${type}`;
      modalAlert.textContent = text;
      modalAlert.style.display = "block";
    }

    function hideAlert() {
      if (!modalAlert) return;
      modalAlert.style.display = "none";
      modalAlert.textContent = "";
    }

    function setTab(tabName) {
      hideAlert();
      if (tabName === "signup") {
        tabSignupBtn?.classList.add("active");
        tabSignupBtn?.setAttribute("aria-selected", "true");
        tabLoginBtn?.classList.remove("active");
        tabLoginBtn?.setAttribute("aria-selected", "false");
        if (loginTab) loginTab.style.display = "none";
        if (signupTab) signupTab.style.display = "block";
        signupForm?.querySelector("input[name='name']")?.focus();
      } else {
        tabLoginBtn?.classList.add("active");
        tabLoginBtn?.setAttribute("aria-selected", "true");
        tabSignupBtn?.classList.remove("active");
        tabSignupBtn?.setAttribute("aria-selected", "false");
        if (signupTab) signupTab.style.display = "none";
        if (loginTab) loginTab.style.display = "block";
        loginForm?.querySelector("input[name='email']")?.focus();
      }
    }

    function openModal(mode = "login", nextTarget = "") {
      hideAlert();
      authModal.classList.add("open");
      authModal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";

      if (nextTarget) {
        loginForm?.querySelectorAll("input[name='next']").forEach((inp) => (inp.value = nextTarget));
        signupForm?.querySelectorAll("input[name='next']").forEach((inp) => (inp.value = nextTarget));
      }

      setTab(mode);
    }

    function closeModal() {
      authModal.classList.remove("open");
      authModal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      hideAlert();
    }

    closeBtn?.addEventListener("click", closeModal);

    authModal.addEventListener("click", (e) => {
      if (e.target === authModal) {
        closeModal();
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && authModal.classList.contains("open")) {
        closeModal();
      }
    });

    tabLoginBtn?.addEventListener("click", () => setTab("login"));
    tabSignupBtn?.addEventListener("click", () => setTab("signup"));
    switchToSignup?.addEventListener("click", (e) => {
      e.preventDefault();
      setTab("signup");
    });
    switchToLogin?.addEventListener("click", (e) => {
      e.preventDefault();
      setTab("login");
    });

    // Wire open buttons
    document.querySelectorAll(".open-auth-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const mode = btn.dataset.authMode || "login";
        const next = btn.dataset.authNext || "";
        openModal(mode, next);
      });
    });

    // Check query params for auto-open (?auth=login or ?auth=signup)
    const urlParams = new URLSearchParams(window.location.search);
    const authAction = urlParams.get("auth");
    if (authAction === "login" || authAction === "signup") {
      const nextParam = urlParams.get("next") || "";
      openModal(authAction, nextParam);
    }

    // Handle AJAX Form Submissions for seamless UX
    async function handleAuthSubmit(form, endpoint) {
      hideAlert();
      const submitBtn = form.querySelector("button[type='submit']");
      const originalText = submitBtn ? submitBtn.innerHTML : "";
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = "Processing...";
      }

      const formData = new FormData(form);
      const payload = {};
      formData.forEach((value, key) => {
        payload[key] = value;
      });

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (response.ok && result.success) {
          showAlert(result.message || "Success! Redirecting...", "success");
          window.setTimeout(() => {
            window.location.href = result.redirect || window.location.pathname;
          }, 400);
        } else {
          showAlert(result.error || "Authentication failed. Please try again.");
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
          }
        }
      } catch (err) {
        // Fallback to standard form submission if fetch/network fails
        form.submit();
      }
    }

    loginForm?.addEventListener("submit", (e) => {
      e.preventDefault();
      handleAuthSubmit(loginForm, loginForm.action);
    });

    signupForm?.addEventListener("submit", (e) => {
      e.preventDefault();
      const pwd = signupForm.querySelector("input[name='password']")?.value;
      const confirmPwd = signupForm.querySelector("input[name='confirm_password']")?.value;
      if (pwd !== confirmPwd) {
        showAlert("Passwords do not match.");
        return;
      }
      handleAuthSubmit(signupForm, signupForm.action);
    });
  }

  // Return / Recovery Confirmation Prompt Modal logic
  const confirmModal = document.getElementById("confirmReturnedModal");
  const returnForm = document.getElementById("markReturnedForm") || document.querySelector("form.mark-returned-form");

  if (confirmModal && returnForm) {
    const closeBtn = document.getElementById("closeConfirmModal");
    const cancelBtn = document.getElementById("cancelConfirmBtn");
    const acceptBtn = document.getElementById("acceptConfirmBtn");
    let isConfirmed = false;
    let lastFocusedElement = null;

    function openConfirmModal() {
      lastFocusedElement = document.activeElement;
      confirmModal.classList.add("open");
      confirmModal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      // Focus cancel button first to prevent accidental confirmation
      if (cancelBtn) {
        cancelBtn.focus();
      }
    }

    function closeConfirmModal() {
      confirmModal.classList.remove("open");
      confirmModal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
        lastFocusedElement.focus();
      }
    }

    returnForm.addEventListener("submit", (e) => {
      if (!isConfirmed) {
        e.preventDefault();
        openConfirmModal();
      }
    });

    cancelBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      closeConfirmModal();
    });

    closeBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      closeConfirmModal();
    });

    acceptBtn?.addEventListener("click", (e) => {
      e.preventDefault();
      isConfirmed = true;
      returnForm.submit();
    });

    confirmModal.addEventListener("click", (e) => {
      if (e.target === confirmModal) {
        closeConfirmModal();
      }
    });

    // Keyboard navigation & accessibility
    document.addEventListener("keydown", (e) => {
      if (!confirmModal.classList.contains("open")) return;

      if (e.key === "Escape") {
        e.preventDefault();
        closeConfirmModal();
      } else if (e.key === "Tab") {
        const focusable = confirmModal.querySelectorAll("button:not([disabled])");
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });
  }
});
