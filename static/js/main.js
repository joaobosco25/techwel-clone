document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("[data-menu-toggle]");
  const nav = document.querySelector("[data-site-nav]");

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("is-open");
      toggle.classList.toggle("is-open", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
    });

    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        nav.classList.remove("is-open");
        toggle.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  const recaptchaKey = document.querySelector('meta[name="recaptcha-site-key"]')?.content || "";

  function ensureRecaptchaLoaded() {
    if (!recaptchaKey || window.grecaptcha) return;
    const script = document.createElement("script");
    script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(recaptchaKey)}`;
    script.async = true;
    document.head.appendChild(script);
  }

  async function getRecaptchaToken(action) {
    if (!recaptchaKey) return "";
    ensureRecaptchaLoaded();
    await new Promise((resolve) => {
      const started = Date.now();
      const timer = setInterval(() => {
        if (window.grecaptcha || Date.now() - started > 5000) {
          clearInterval(timer);
          resolve();
        }
      }, 120);
    });
    if (!window.grecaptcha) return "";
    return new Promise((resolve) => {
      window.grecaptcha.ready(async () => {
        try {
          const token = await window.grecaptcha.execute(recaptchaKey, { action });
          resolve(token || "");
        } catch (_error) {
          resolve("");
        }
      });
    });
  }

  function setMessage(form, text, ok = true, whatsapp = "") {
    const message = form.querySelector(".success, .form-status");
    if (!message) return;
    message.textContent = text;
    message.classList.add("show");
    message.classList.toggle("error", !ok);

    if (!ok && whatsapp) {
      const link = document.createElement("a");
      link.href = whatsapp;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = " Falar no WhatsApp";
      message.appendChild(link);
    }
  }



  function maskCep(value) {
    const digits = String(value || "").replace(/\D/g, "").slice(0, 8);
    if (digits.length <= 5) return digits;
    return `${digits.slice(0, 5)}-${digits.slice(5)}`;
  }

  async function validateCepField(cepInput, showMessage = false) {
    if (!cepInput) return true;
    const cep = cepInput.value.replace(/\D/g, "");

    if (cep.length !== 8) {
      cepInput.setCustomValidity("Informe um CEP válido com 8 números.");
      if (showMessage) cepInput.reportValidity();
      return false;
    }

    try {
      cepInput.setCustomValidity("Validando CEP...");
      const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      if (!response.ok) throw new Error("viacep_unavailable");
      const data = await response.json();

      if (data.erro) {
        cepInput.setCustomValidity("Informe um CEP existente.");
        if (showMessage) cepInput.reportValidity();
        return false;
      }

      const cityTarget = cepInput.dataset.cityTarget;
      const stateTarget = cepInput.dataset.stateTarget;
      const addressTarget = cepInput.dataset.addressTarget;
      const cityInput = cityTarget ? document.querySelector(cityTarget) : null;
      const stateInput = stateTarget ? document.querySelector(stateTarget) : null;
      const addressInput = addressTarget ? document.querySelector(addressTarget) : null;

      if (cityInput && data.localidade) cityInput.value = data.localidade;
      if (stateInput && data.uf) stateInput.value = data.uf;
      if (addressInput && data.logradouro && !addressInput.value.trim()) addressInput.value = data.logradouro;

      cepInput.setCustomValidity("");
      return true;
    } catch (_error) {
      // Se o ViaCEP estiver indisponível no navegador, o backend ainda valida no envio.
      cepInput.setCustomValidity("");
      return true;
    }
  }

  async function validateAllCepLookups(root, showMessage = false) {
    const inputs = Array.from(root.querySelectorAll("[data-cep-lookup]"));
    for (const input of inputs) {
      const ok = await validateCepField(input, showMessage);
      if (!ok) {
        input.focus();
        return false;
      }
    }
    return true;
  }

  function setupCepAutofill() {
    document.querySelectorAll("[data-cep-lookup]").forEach((input) => {
      input.addEventListener("input", () => {
        input.value = maskCep(input.value);
        input.setCustomValidity("");
        if (input.value.replace(/\D/g, "").length === 8) validateCepField(input, false);
      });
      input.addEventListener("blur", () => validateCepField(input, true));
    });
  }

  function setupSteppedForms() {
    document.querySelectorAll("[data-form-steps]").forEach((stepsRoot) => {
      const form = stepsRoot.closest("form");
      const tabs = Array.from(stepsRoot.querySelectorAll("[data-step-target]"));
      const steps = Array.from(stepsRoot.querySelectorAll("[data-step]"));
      const cepInput = form?.querySelector("#cep");
      const ruaInput = form?.querySelector("#rua");
      const reviewBox = stepsRoot.querySelector("[data-review-box]");
      let currentStep = 1;
      let maxReachedStep = 1;
      let cepValidationController = null;
      let lastValidatedCep = "";
      let lastCepWasValid = false;

      function fieldsForStep(stepNumber) {
        return Array.from(stepsRoot.querySelector(`[data-step="${stepNumber}"]`)?.querySelectorAll("input, select, textarea") || [])
          .filter((field) => !field.disabled && field.type !== "hidden");
      }

      function getSelectedRadioValue(name) {
        return form?.querySelector(`input[name="${name}"]:checked`)?.value || "-";
      }

      async function validateCepOnline(showMessage = false) {
        if (!cepInput) return true;
        const cep = cepInput.value.replace(/\D/g, "");

        if (cep.length !== 8) {
          lastValidatedCep = "";
          lastCepWasValid = false;
          cepInput.setCustomValidity("Informe um CEP válido com 8 números.");
          if (showMessage) cepInput.reportValidity();
          return false;
        }

        if (cep === lastValidatedCep && lastCepWasValid) {
          cepInput.setCustomValidity("");
          return true;
        }

        if (cepValidationController) cepValidationController.abort();
        cepValidationController = new AbortController();

        try {
          cepInput.setCustomValidity("Validando CEP...");
          const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`, {
            signal: cepValidationController.signal,
          });
          if (!response.ok) throw new Error("viacep_unavailable");
          const data = await response.json();

          if (data.erro) {
            lastValidatedCep = cep;
            lastCepWasValid = false;
            cepInput.setCustomValidity("Informe um CEP existente.");
            if (showMessage) cepInput.reportValidity();
            return false;
          }

          lastValidatedCep = cep;
          lastCepWasValid = true;
          cepInput.setCustomValidity("");
          if (ruaInput && data.logradouro) ruaInput.value = data.logradouro;
          return true;
        } catch (error) {
          if (error.name === "AbortError") return false;
          // Se o ViaCEP estiver indisponível no navegador, o backend ainda fará a validação ao enviar.
          cepInput.setCustomValidity("");
          return true;
        }
      }

      async function validateStep(stepNumber) {
        if (stepNumber === 1 && cepInput) {
          const cepOk = await validateCepOnline(true);
          if (!cepOk) {
            cepInput.focus();
            return false;
          }
        }

        const fields = fieldsForStep(stepNumber);
        for (const field of fields) {
          if (!field.checkValidity()) {
            field.reportValidity();
            field.focus();
            return false;
          }
        }
        return true;
      }

      function updateReview() {
        if (!reviewBox || !form) return;
        const items = [
          ["CEP", form.cep?.value || "-"],
          ["Rua", form.rua?.value || "-"],
          ["Número", form.numero?.value || "-"],
          ["Nome completo", form.nome_completo?.value || "-"],
          ["E-mail", form.email?.value || "-"],
          ["Situação do cliente", getSelectedRadioValue("tipo_cliente")],
          ["Descrição do problema", form.descricao?.value || "-"],
        ];
        reviewBox.innerHTML = items.map(([label, value]) => `
          <div class="review-item">
            <strong>${label}</strong>
            <span>${String(value).replace(/[<>&]/g, (char) => ({"<":"&lt;", ">":"&gt;", "&":"&amp;"}[char]))}</span>
          </div>
        `).join("");
      }

      function showStep(stepNumber) {
        currentStep = stepNumber;
        maxReachedStep = Math.max(maxReachedStep, stepNumber);
        steps.forEach((step) => {
          const isActive = Number(step.dataset.step) === stepNumber;
          step.classList.toggle("active", isActive);
          step.hidden = !isActive;
        });
        tabs.forEach((tab) => {
          const target = Number(tab.dataset.stepTarget);
          const isActive = target === stepNumber;
          const isLocked = target > maxReachedStep;
          tab.classList.toggle("active", isActive);
          tab.setAttribute("aria-selected", String(isActive));
          tab.setAttribute("aria-disabled", String(isLocked));
        });
        if (stepNumber === 3) updateReview();
        stepsRoot.scrollIntoView({ behavior: "smooth", block: "start" });
      }

      tabs.forEach((tab) => {
        tab.addEventListener("click", async () => {
          const target = Number(tab.dataset.stepTarget);
          if (target > maxReachedStep) return;
          if (target > currentStep && !(await validateStep(currentStep))) return;
          if (target === 3 && !(await validateStep(1))) return;
          if (target === 3 && !(await validateStep(2))) return;
          showStep(target);
        });
      });

      stepsRoot.querySelectorAll("[data-next-step]").forEach((button) => {
        button.addEventListener("click", async () => {
          if (!(await validateStep(currentStep))) return;
          showStep(Math.min(currentStep + 1, steps.length));
        });
      });

      stepsRoot.querySelectorAll("[data-prev-step]").forEach((button) => {
        button.addEventListener("click", () => showStep(Math.max(currentStep - 1, 1)));
      });

      if (cepInput) {
        cepInput.addEventListener("input", () => {
          cepInput.value = maskCep(cepInput.value);
          lastValidatedCep = "";
          lastCepWasValid = false;
          cepInput.setCustomValidity("");
          const cep = cepInput.value.replace(/\D/g, "");
          if (cep.length === 8) validateCepOnline(false);
        });
        cepInput.addEventListener("blur", () => validateCepOnline(true));
      }

      showStep(1);
    });
  }

  function toggleButton(form, disabled) {
    const button = form.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = disabled;
      button.dataset.originalText = button.dataset.originalText || button.textContent;
      button.textContent = disabled ? "Enviando..." : button.dataset.originalText;
    }
  }

  setupCepAutofill();
  setupSteppedForms();

  document.querySelectorAll("form[data-ajax-form]").forEach((form) => {
    ensureRecaptchaLoaded();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      if (!(await validateAllCepLookups(form, true))) {
        return;
      }

      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      toggleButton(form, true);
      setMessage(form, "Enviando sua solicitação...", true);

      const formData = new FormData(form);
      const token = await getRecaptchaToken(formData.get("form_type") || "formulario");
      if (token) formData.set("recaptcha_token", token);

      try {
        const response = await fetch(form.action || "/api/formulario", {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "fetch" },
        });
        const result = await response.json();
        setMessage(form, result.message || (response.ok ? "Enviado com sucesso." : "Não foi possível enviar."), response.ok && result.ok, result.whatsapp || "");
        if (response.ok && result.ok) {
          form.reset();
          const stepsRoot = form.querySelector("[data-form-steps]");
          if (stepsRoot) {
            stepsRoot.querySelectorAll("[data-step]").forEach((step) => {
              const isFirst = step.dataset.step === "1";
              step.classList.toggle("active", isFirst);
              step.hidden = !isFirst;
            });
            stepsRoot.querySelectorAll("[data-step-target]").forEach((tab) => {
              const isFirst = tab.dataset.stepTarget === "1";
              tab.classList.toggle("active", isFirst);
              tab.setAttribute("aria-selected", String(isFirst));
              tab.setAttribute("aria-disabled", String(!isFirst));
            });
          }
        }
      } catch (_error) {
        setMessage(form, "Não foi possível enviar agora. Tente novamente ou fale conosco pelo WhatsApp.", false, "https://wa.me/5532984560451?text=N%C3%A3o%20consegui%20enviar%20o%20formul%C3%A1rio%20pelo%20site%20da%20TechWel.");
      } finally {
        toggleButton(form, false);
      }
    });
  });

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));
});
