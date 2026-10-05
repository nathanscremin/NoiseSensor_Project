const alertStateLabels = {
    normal: "Normal",
    pending_alert: "Aguardando ativação",
    alert: "Em alerta",
    pending_recovery: "Aguardando recuperação",
};

const alertStateClasses = {
    normal: "alert-state-normal",
    pending_alert: "alert-state-pending",
    alert: "alert-state-active",
    pending_recovery: "alert-state-recovery",
};

let lastAlertState = null;

function getAlertStateLabel(state) {
    return alertStateLabels[state] || "Desconhecido";
}

function formatAlertDuration(startedAt, endedAt) {
    const start = new Date(startedAt);
    const end = endedAt ? new Date(endedAt) : new Date();

    const seconds = Math.max(
        0,
        Math.round((end.getTime() - start.getTime()) / 1000)
    );

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    if (hours > 0) {
        return `${hours}h ${minutes}min`;
    }

    if (minutes > 0) {
        return `${minutes}min ${remainingSeconds}s`;
    }

    return `${remainingSeconds}s`;
}

function formatAlertTimestamp(timestamp) {
    if (!timestamp) {
        return "Em andamento";
    }

    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "Data indisponível";
    }

    return date.toLocaleString("pt-BR");
}

async function fetchAlertSettings(sensorId) {
    const response = await fetch(
        `/api/sensors/${sensorId}/alert-settings`,
        {
            method: "GET",
            credentials: "same-origin",
        }
    );

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Sessão expirada.");
    }

    if (!response.ok) {
        throw new Error(
            `Erro ao carregar configuração do alerta: ${response.status}`
        );
    }

    return response.json();
}

async function fetchAlertHistory(sensorId) {
    const response = await fetch(
        `/api/sensors/${sensorId}/alerts?limit=20`,
        {
            method: "GET",
            credentials: "same-origin",
        }
    );

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Sessão expirada.");
    }

    if (!response.ok) {
        throw new Error(
            `Erro ao carregar histórico de alertas: ${response.status}`
        );
    }

    return response.json();
}

function applyAlertStateToBadge(state) {
    const badge = document.getElementById("selected-sensor-alert-state");

    if (!badge) {
        return;
    }

    for (const className of Object.values(alertStateClasses)) {
        badge.classList.remove(className);
    }

    badge.classList.add(
        alertStateClasses[state] || "alert-state-normal"
    );

    badge.textContent = `Estado do alerta: ${getAlertStateLabel(state)}`;
}

function populateAlertSettingsForm(settings) {
    const thresholdInput = document.getElementById("alert-threshold-db");
    const triggerInput = document.getElementById("alert-trigger-duration");
    const recoveryInput = document.getElementById("alert-recovery-duration");

    if (!thresholdInput || !triggerInput || !recoveryInput) {
        return;
    }

    thresholdInput.value = settings.threshold_db;
    triggerInput.value = settings.trigger_duration_seconds;
    recoveryInput.value = settings.recovery_duration_seconds;
}

function renderAlertHistory(alerts) {
    const container = document.getElementById("alert-history-content");

    if (!container) {
        return;
    }

    if (!alerts.length) {
        container.innerHTML = `
            <div class="empty-state-block">
                <p>Nenhum alerta registrado para este sensor.</p>
                <span>Quando um episódio acontecer, ele aparecerá aqui.</span>
            </div>
        `;
        return;
    }

    const rows = alerts.map((alert) => {
        const active = !alert.ended_at;
        const duration = formatAlertDuration(
            alert.started_at,
            alert.ended_at
        );

        return `
            <article class="alert-history-item ${active ? "alert-history-active" : ""}">
                <div class="alert-history-main">
                    <div>
                        <span class="alert-history-label">
                            ${active ? "Alerta em andamento" : "Alerta encerrado"}
                        </span>
                        <strong>
                            ${formatAlertTimestamp(alert.started_at)}
                        </strong>
                    </div>

                    <span class="alert-history-peak">
                        Pico: ${Number(alert.peak_noise_db).toFixed(2)} dB
                    </span>
                </div>

                <div class="alert-history-details">
                    <span>
                        Limite: ${Number(alert.threshold_db).toFixed(2)} dB
                    </span>
                    <span>
                        Fim: ${formatAlertTimestamp(alert.ended_at)}
                    </span>
                    <span>
                        Duração: ${duration}
                    </span>
                </div>
            </article>
        `;
    });

    container.innerHTML = rows.join("");
}

function showAlertSettingsMessage(message, type = "") {
    const element = document.getElementById("alert-settings-message");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `form-message ${type}`.trim();
}

async function saveAlertSettings(event) {
    event.preventDefault();

    if (window.selectedSensorId === null) {
        showAlertSettingsMessage(
            "Selecione um sensor antes de salvar."
        );
        return;
    }

    const button = document.getElementById("save-alert-settings");
    const form = event.currentTarget;

    const formData = new FormData(form);

    const data = {
        threshold_db: Number(formData.get("threshold_db")),
        trigger_duration_seconds: Number(
            formData.get("trigger_duration_seconds")
        ),
        recovery_duration_seconds: Number(
            formData.get("recovery_duration_seconds")
        ),
    };

    if (
        !Number.isFinite(data.threshold_db) ||
        data.threshold_db <= 0 ||
        data.threshold_db > 200
    ) {
        showAlertSettingsMessage(
            "Informe um limite entre 0,01 e 200 dB.",
            "error"
        );
        return;
    }

    if (
        !Number.isInteger(data.trigger_duration_seconds) ||
        data.trigger_duration_seconds < 1
    ) {
        showAlertSettingsMessage(
            "O tempo para entrar em alerta deve ser de pelo menos 1 segundo.",
            "error"
        );
        return;
    }

    if (
        !Number.isInteger(data.recovery_duration_seconds) ||
        data.recovery_duration_seconds < 1
    ) {
        showAlertSettingsMessage(
            "O tempo para sair do alerta deve ser de pelo menos 1 segundo.",
            "error"
        );
        return;
    }

    button.disabled = true;
    showAlertSettingsMessage("Salvando...");

    try {
        const response = await fetch(
            `/api/sensors/${window.selectedSensorId}/alert-settings`,
            {
                method: "PUT",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            }
        );

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Não foi possível salvar a configuração."
            );
        }

        populateAlertSettingsForm(result);
        applyAlertStateToBadge(result.state);
        lastAlertState = result.state;

        showAlertSettingsMessage(
            "Configuração salva com sucesso.",
            "success"
        );
    } catch (error) {
        console.error("Erro ao salvar configuração de alerta:", error);

        showAlertSettingsMessage(
            error.message || "Não foi possível salvar a configuração.",
            "error"
        );
    } finally {
        button.disabled = false;
    }
}

async function loadAlertDetails(sensorId) {
    const [settings, alerts] = await Promise.all([
        fetchAlertSettings(sensorId),
        fetchAlertHistory(sensorId),
    ]);

    populateAlertSettingsForm(settings);
    applyAlertStateToBadge(settings.state);
    renderAlertHistory(alerts);

    lastAlertState = settings.state;

    const form = document.getElementById("alert-settings-form");

    if (form) {
        form.addEventListener("submit", saveAlertSettings);
    }
}

async function refreshAlertState(sensorId) {
    const settings = await fetchAlertSettings(sensorId);

    applyAlertStateToBadge(settings.state);

    if (lastAlertState !== settings.state) {
        lastAlertState = settings.state;

        const alerts = await fetchAlertHistory(sensorId);
        renderAlertHistory(alerts);
    }
}
