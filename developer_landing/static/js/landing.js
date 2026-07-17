(() => {
  const form = document.getElementById("contact-form");
  const statusEl = document.getElementById("form-status");
  const submitBtn = document.getElementById("submit-btn");

  if (!form || !statusEl || !submitBtn) {
    return;
  }

  const field = (id) => form.querySelector(`#${id}`);

  const setStatus = (message, type) => {
    statusEl.textContent = message;
    statusEl.classList.remove("is-error", "is-success");
    if (type) {
      statusEl.classList.add(type);
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    event.stopPropagation();

    setStatus("Отправляем…", null);
    submitBtn.disabled = true;

    const payload = {
      name: (field("name")?.value || "").trim(),
      phone: (field("phone")?.value || "").trim(),
      email: (field("email")?.value || "").trim(),
      comment: (field("comment")?.value || "").trim(),
    };

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (response.status === 201 && data.success) {
        const id = data.data?.id ?? "?";
        let message = `Спасибо! Обращение #${id} принято.`;
        if (data.data?.ai_available && data.data?.request_type) {
          message += `\nAI статистика: +1 ${data.data.request_type}.`;
        } else {
          message += "\nAI статистика: тип не определён (AI недоступен).";
        }
        setStatus(message, "is-success");
        form.reset();
        return;
      }

      if (response.status === 429) {
        const retry = data.error?.retry_after;
        setStatus(
          retry
            ? `Слишком много запросов. Повторите через ${retry} сек.`
            : "Слишком много запросов. Попробуйте позже.",
          "is-error",
        );
        return;
      }

      if (response.status === 400) {
        const details = data.error?.details;
        const first =
          details && typeof details === "object"
            ? Object.values(details).flat()[0]
            : null;
        setStatus(first || "Проверьте поля формы.", "is-error");
        return;
      }

      setStatus(
        (typeof data.error?.details === "string" && data.error.details) ||
          "Не удалось отправить. Попробуйте позже.",
        "is-error",
      );
    } catch (_error) {
      setStatus("Сеть недоступна. Проверьте соединение.", "is-error");
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
