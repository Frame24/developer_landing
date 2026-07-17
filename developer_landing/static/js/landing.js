(() => {
  const form = document.getElementById("contact-form");
  const statusEl = document.getElementById("form-status");
  const submitBtn = document.getElementById("submit-btn");
  const refreshDemoBtn = document.getElementById("refresh-demo");
  const demoHealth = document.getElementById("demo-health");
  const demoMetrics = document.getElementById("demo-metrics");
  const demoMail = document.getElementById("demo-mail");

  const field = (id) => form?.querySelector(`#${id}`);

  const setStatus = (message, type) => {
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.classList.remove("is-error", "is-success");
    if (type) {
      statusEl.classList.add(type);
    }
  };

  const pretty = (value) => JSON.stringify(value, null, 2);

  const loadDemoPanels = async () => {
    if (!demoHealth || !demoMetrics || !demoMail) {
      return;
    }
    try {
      const [healthRes, metricsRes, mailRes] = await Promise.all([
        fetch("/api/health"),
        fetch("/api/metrics"),
        fetch("/api/mail?limit=8"),
      ]);
      const health = await healthRes.json();
      const metrics = await metricsRes.json();
      const mail = await mailRes.json();
      demoHealth.textContent = `GET /api/health\n${pretty(health)}`;
      demoMetrics.textContent = `GET /api/metrics\n${pretty(metrics)}`;
      const items = (mail.data?.items || []).map((item) => ({
        kind: item.kind,
        subject: item.subject,
        original_email: item.original_email,
        delivery_to: item.delivery_to,
        modified_at: item.modified_at,
        preview: item.preview,
      }));
      demoMail.textContent = `GET /api/mail\n${pretty({
        success: mail.success,
        demo_force_to: mail.data?.demo_force_to,
        count: mail.data?.count,
        items,
      })}`;
    } catch (_error) {
      demoHealth.textContent = "health: ошибка загрузки";
      demoMetrics.textContent = "metrics: ошибка загрузки";
      demoMail.textContent = "mail: ошибка загрузки";
    }
  };

  if (form && statusEl && submitBtn) {
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
          if (data.data?.request_type) {
            message += `\nAI статистика: +1 ${data.data.request_type}.`;
          } else {
            message += "\nAI статистика: тип не определён.";
          }
          if (data.data?.email_delivery_to) {
            message += `\nПисьма (owner + ответ): ${data.data.email_delivery_to}`;
          }
          setStatus(message, "is-success");
          form.reset();
          loadDemoPanels();
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
  }

  refreshDemoBtn?.addEventListener("click", () => {
    loadDemoPanels();
  });

  loadDemoPanels();
})();
