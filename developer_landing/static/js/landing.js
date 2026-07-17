(() => {
  const form = document.getElementById("contact-form");
  const statusEl = document.getElementById("form-status");
  const submitBtn = document.getElementById("submit-btn");
  const refreshMailBtn = document.getElementById("refresh-mail");
  const mailListEl = document.getElementById("mail-list");
  const mailReadEl = document.getElementById("mail-read");
  const metricContacts = document.getElementById("metric-contacts");
  const metricAi = document.getElementById("metric-ai");
  const metricMail = document.getElementById("metric-mail");

  let mailItems = [];
  let selectedFilename = null;

  const field = (id) => form?.querySelector(`#${id}`);

  const setStatus = (message, type) => {
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.classList.remove("is-error", "is-success");
    if (type) {
      statusEl.classList.add(type);
    }
  };

  const kindLabel = (kind) => {
    if (kind === "owner") return "владельцу";
    if (kind === "user_reply") return "ответ";
    return kind || "письмо";
  };

  const formatTime = (iso) => {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  const renderMailRead = (item) => {
    if (!mailReadEl) return;
    if (!item) {
      mailReadEl.innerHTML = '<p class="mail-empty">Выберите письмо слева</p>';
      return;
    }
    mailReadEl.innerHTML = `
      <div class="mail-read-meta">
        <div><strong>${escapeHtml(item.subject || "Без темы")}</strong></div>
        <div>Тип: ${escapeHtml(kindLabel(item.kind))}</div>
        <div>С формы: ${escapeHtml(item.original_email || "—")}</div>
        <div>Доставка: ${escapeHtml(item.delivery_to || "—")}</div>
        <div>Время: ${escapeHtml(formatTime(item.modified_at))}</div>
      </div>
      <pre class="mail-read-body">${escapeHtml(item.body || item.preview || "")}</pre>
    `;
  };

  const renderMailList = () => {
    if (!mailListEl) return;
    if (!mailItems.length) {
      mailListEl.innerHTML = '<p class="mail-empty">Пока писем нет. Отправьте форму.</p>';
      renderMailRead(null);
      return;
    }

    mailListEl.innerHTML = mailItems
      .map((item) => {
        const active = item.filename === selectedFilename ? " is-active" : "";
        return `
          <button type="button" class="mail-item${active}" data-filename="${escapeHtml(item.filename)}" role="listitem">
            <span class="mail-item-top">
              <span class="mail-kind">${escapeHtml(kindLabel(item.kind))}</span>
              <span class="mail-time">${escapeHtml(formatTime(item.modified_at))}</span>
            </span>
            <span class="mail-subject">${escapeHtml(item.subject || "Без темы")}</span>
            <span class="mail-from">${escapeHtml(item.original_email || item.delivery_to || "")}</span>
          </button>
        `;
      })
      .join("");
  };

  const selectMail = (filename) => {
    selectedFilename = filename;
    const item = mailItems.find((entry) => entry.filename === filename) || null;
    renderMailList();
    renderMailRead(item);
  };

  const loadMetrics = async () => {
    if (!metricContacts || !metricAi || !metricMail) return;
    try {
      const response = await fetch("/api/metrics");
      const payload = await response.json();
      const file = payload.data?.file_metrics || {};
      const contacts = payload.data?.db_total ?? file.total_contacts ?? "—";
      const aiOk = file.ai_success ?? "—";
      const mailSent =
        (Number(file.emails_sent || 0) || 0) +
        (Number(file.emails_smtp_queued || 0) || 0) +
        (Number(file.emails_file_fallback || 0) || 0);
      metricContacts.textContent = String(contacts);
      metricAi.textContent = String(aiOk);
      metricMail.textContent = String(mailSent);
    } catch (_error) {
      metricContacts.textContent = "?";
      metricAi.textContent = "?";
      metricMail.textContent = "?";
    }
  };

  const loadMailbox = async () => {
    if (!mailListEl) return;
    try {
      const response = await fetch("/api/mail?limit=20");
      const payload = await response.json();
      mailItems = payload.data?.items || [];
      if (
        selectedFilename &&
        !mailItems.some((item) => item.filename === selectedFilename)
      ) {
        selectedFilename = null;
      }
      if (!selectedFilename && mailItems[0]) {
        selectedFilename = mailItems[0].filename;
      }
      renderMailList();
      renderMailRead(
        mailItems.find((item) => item.filename === selectedFilename) || null,
      );
    } catch (_error) {
      mailListEl.innerHTML = '<p class="mail-empty">Не удалось загрузить почту</p>';
      renderMailRead(null);
    }
  };

  const refreshPanels = async () => {
    await Promise.all([loadMetrics(), loadMailbox()]);
  };

  mailListEl?.addEventListener("click", (event) => {
    const button = event.target.closest(".mail-item");
    if (!button) return;
    selectMail(button.dataset.filename);
  });

  refreshMailBtn?.addEventListener("click", () => {
    refreshPanels();
  });

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
          setStatus(`Спасибо! Обращение #${id} принято.`, "is-success");
          form.reset();
          refreshPanels();
          // AI + mail finish in background; refresh again shortly.
          window.setTimeout(refreshPanels, 2500);
          window.setTimeout(refreshPanels, 6000);
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

  refreshPanels();
})();
