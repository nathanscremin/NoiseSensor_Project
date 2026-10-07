const sensorsContainer = document.getElementById("sensor-details");
const connectionIndicator = document.getElementById("connection-indicator");
const connectionText = document.getElementById("connection-text");
const currentUserName = document.getElementById("current-user-name");
const logoutButton = document.getElementById("logout-button");
const adminPanelButton = document.getElementById("admin-panel-button");

let sensors = [];
let selectedSensorId = null;
window.selectedSensorId = null;
let historyChart = null;
let predictionChart = null;
let sensorMap = null;

const SENSOR_REFRESH_INTERVAL_MS = 1000;
const DETAIL_REFRESH_INTERVAL_MS = 5000;
let lastDetailRefreshAt = 0;
let lastDetailHourKey = null;

function redirectToLogin() {
    window.location.href = "/login";
}

async function getCurrentUser() {
    const response = await fetch("/api/auth/me", {
        method: "GET",
        credentials: "same-origin",
    });

    if (response.status === 401) {
        redirectToLogin();
        return null;
    }

    if (!response.ok) {
        throw new Error(
            `Erro ao verificar autenticação: ${response.status}`
        );
    }

    return response.json();
}

async function logout() {
    logoutButton.disabled = true;

    try {
        const response = await fetch("/api/auth/logout", {
            method: "POST",
            credentials: "same-origin",
        });

        if (!response.ok && response.status !== 401) {
            throw new Error(
                `Erro ao encerrar sessão: ${response.status}`
            );
        }
    } catch (error) {
        console.error("Erro durante o logout:", error);
    } finally {
        redirectToLogin();
    }
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "Data indisponível";
    }

    return date.toLocaleString("pt-BR");
}

function formatChartTime(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "--:--";
    }

    return date.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

async function fetchHistory(sensorId) {
    const response = await fetch(
        `/api/sensors/${sensorId}/history`,
        { credentials: "same-origin" }
    );

    if (response.status === 401) {
        redirectToLogin();
        throw new Error("Sessão expirada.");
    }

    if (!response.ok) {
        throw new Error(
            `Erro ao carregar histórico: ${response.status}`
        );
    }

    return response.json();
}

async function fetchPredictions(sensorId) {
    const response = await fetch(
        `/api/sensors/${sensorId}/predictions`,
        { credentials: "same-origin" }
    );

    if (response.status === 401) {
        redirectToLogin();
        throw new Error("Sessão expirada.");
    }

    if (!response.ok) {
        throw new Error(
            `Erro ao carregar previsões: ${response.status}`
        );
    }

    return response.json();
}

function destroyCharts() {
    if (historyChart) {
        historyChart.destroy();
        historyChart = null;
    }

    if (predictionChart) {
        predictionChart.destroy();
        predictionChart = null;
    }
}

function formatNoise(sensor) {
    if (sensor.noise_db === null || sensor.noise_db === undefined) {
        return "Aguardando leitura";
    }

    return `${Number(sensor.noise_db).toFixed(2)} dB`;
}

function getCurrentHourKey() {
    const now = new Date();

    return [
        now.getFullYear(),
        now.getMonth(),
        now.getDate(),
        now.getHours(),
    ].join("-");
}

function shouldRefreshSensorDetails() {
    const now = Date.now();
    const currentHourKey = getCurrentHourKey();

    if (lastDetailHourKey !== currentHourKey) {
        return true;
    }

    return now - lastDetailRefreshAt >= DETAIL_REFRESH_INTERVAL_MS;
}

function renderSensorDetails(sensor) {
    sensorsContainer.innerHTML = `
        <article class="sensor-details-card">
            <div class="sensor-header">
                <div class="sensor-heading">
                    <h2 id="selected-sensor-name" class="sensor-name">
                        ${sensor.name}
                    </h2>
                    <p id="selected-sensor-region" class="sensor-region">
                        Região: ${sensor.region}
                    </p>
                </div>

                <div id="selected-sensor-noise" class="sensor-noise">
                    ${formatNoise(sensor)}
                </div>
            </div>

            <div class="sensor-badges">
                <span id="selected-sensor-status" class="sensor-status">
                    ${sensor.status}
                </span>

                <span id="selected-sensor-alert-state" class="alert-state-badge alert-state-normal">
                    Estado do alerta: Normal
                </span>
            </div>

            <div class="sensor-footer">
                <span>Última coleta:</span>
                <span id="selected-sensor-timestamp">
                    ${sensor.read_timestamp ? formatTimestamp(sensor.read_timestamp) : "Aguardando primeira leitura"}
                </span>
            </div>
        </article>

        <section class="chart-section">
            <div class="section-heading">
                <div>
                    <h3>Histórico</h3>
                    <p>Últimas 24 horas</p>
                </div>
            </div>

            <div class="chart-container">
                <canvas id="history-chart"></canvas>
            </div>

            <p id="history-empty" class="empty-state hidden">
                Ainda não há dados suficientes para exibir o histórico.
            </p>
        </section>

        <section class="chart-section">
            <div class="section-heading">
                <div>
                    <h3>Previsão</h3>
                    <p>Próximas 24 horas</p>
                </div>
            </div>

            <div class="chart-container">
                <canvas id="prediction-chart"></canvas>
            </div>

            <p id="prediction-empty" class="empty-state hidden">
                Ainda não há previsões disponíveis para este sensor.
            </p>
        </section>

        <section id="alert-history-section" class="alert-section">
            <div class="section-heading">
                <div>
                    <h3>Histórico de alertas</h3>
                    <p>Últimos episódios registrados para este sensor.</p>
                </div>
            </div>

            <div id="alert-history-content" class="alert-history-content">
                <p class="loading">Carregando histórico de alertas...</p>
            </div>
        </section>

        <section id="alert-settings-section" class="alert-section alert-settings-section">
            <div class="section-heading">
                <div>
                    <h3>Configuração do alerta</h3>
                    <p>Defina quando este sensor deve entrar e sair do estado de alerta.</p>
                </div>
            </div>

            <form id="alert-settings-form" class="alert-settings-form">
                <div class="form-field">
                    <label for="alert-threshold-db">Limite de ruído (dB)</label>
                    <input
                        id="alert-threshold-db"
                        name="threshold_db"
                        type="number"
                        min="0.01"
                        max="200"
                        step="0.01"
                        required
                    >
                    <span class="field-help">Quando a leitura for igual ou maior que este valor.</span>
                </div>

                <div class="form-field">
                    <label for="alert-trigger-duration">Tempo para entrar em alerta (segundos)</label>
                    <input
                        id="alert-trigger-duration"
                        name="trigger_duration_seconds"
                        type="number"
                        min="1"
                        max="86400"
                        step="1"
                        required
                    >
                    <span class="field-help">Tempo contínuo acima do limite necessário para ativar o alerta.</span>
                </div>

                <div class="form-field">
                    <label for="alert-recovery-duration">Tempo para sair do alerta (segundos)</label>
                    <input
                        id="alert-recovery-duration"
                        name="recovery_duration_seconds"
                        type="number"
                        min="1"
                        max="86400"
                        step="1"
                        required
                    >
                    <span class="field-help">Tempo contínuo abaixo do limite necessário para encerrar o alerta.</span>
                </div>

                <div class="alert-settings-actions">
                    <button id="save-alert-settings" class="primary-button" type="submit">
                        Salvar configuração
                    </button>
                    <span id="alert-settings-message" class="form-message" aria-live="polite"></span>
                </div>
            </form>
        </section>
    `;
}

function updateSelectedSensorSummary(sensor) {
    const nameElement = document.getElementById("selected-sensor-name");
    const regionElement = document.getElementById("selected-sensor-region");
    const noiseElement = document.getElementById("selected-sensor-noise");
    const statusElement = document.getElementById("selected-sensor-status");
    const timestampElement = document.getElementById("selected-sensor-timestamp");

    if (
        !nameElement ||
        !regionElement ||
        !noiseElement ||
        !statusElement ||
        !timestampElement
    ) {
        return;
    }

    nameElement.textContent = sensor.name;
    regionElement.textContent = `Região: ${sensor.region}`;
    noiseElement.textContent = formatNoise(sensor);
    statusElement.textContent = sensor.status;
    timestampElement.textContent = sensor.read_timestamp
        ? formatTimestamp(sensor.read_timestamp)
        : "Aguardando primeira leitura";
}

function createHistoryChart(history) {
    const canvas = document.getElementById("history-chart");
    const emptyState = document.getElementById("history-empty");

    if (!canvas || !emptyState) {
        return;
    }

    if (!history.length) {
        canvas.classList.add("hidden");
        emptyState.classList.remove("hidden");
        return;
    }

    canvas.classList.remove("hidden");
    emptyState.classList.add("hidden");

    const labels = history.map((item) => formatChartTime(item.timestamp));
    const values = history.map((item) => item.avg_noise_db);

    if (historyChart) {
        historyChart.data.labels = labels;
        historyChart.data.datasets[0].data = values;
        historyChart.update("none");
        return;
    }

    historyChart = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Ruído médio",
                    data: values,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                },
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: "dB",
                    },
                },
            },
        },
    });
}

function createPredictionChart(predictions) {
    const canvas = document.getElementById("prediction-chart");
    const emptyState = document.getElementById("prediction-empty");

    if (!canvas || !emptyState) {
        return;
    }

    if (!predictions.length) {
        canvas.classList.add("hidden");
        emptyState.classList.remove("hidden");
        return;
    }

    canvas.classList.remove("hidden");
    emptyState.classList.add("hidden");

    const labels = predictions.map((item) => formatChartTime(item.timestamp));
    const values = predictions.map((item) => item.predicted_noise_db);

    if (predictionChart) {
        predictionChart.data.labels = labels;
        predictionChart.data.datasets[0].data = values;
        predictionChart.update("none");
        return;
    }

    predictionChart = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Previsão",
                    data: values,
                    tension: 0.3,
                    borderWidth: 2,
                    pointRadius: 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                },
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: "dB",
                    },
                },
            },
        },
    });
}

async function loadSensorDetails(sensorId) {
    const sensor = sensors.find((item) => item.sensor_id === sensorId);

    if (!sensor) {
        return;
    }

    selectedSensorId = sensorId;
    window.selectedSensorId = sensorId;
    lastDetailRefreshAt = 0;
    lastDetailHourKey = null;
    destroyCharts();
    renderSensorDetails(sensor);

    try {
        const [history, predictions] = await Promise.all([
            fetchHistory(sensorId),
            fetchPredictions(sensorId),
        ]);

        if (selectedSensorId !== sensorId) {
            return;
        }

        createHistoryChart(history);
        createPredictionChart(predictions);

        try {
            await loadAlertDetails(sensorId);
        } catch (alertError) {
            console.error(
                "Erro ao carregar os alertas do sensor:",
                alertError
            );

            const alertHistoryContent = document.getElementById(
                "alert-history-content"
            );

            if (alertHistoryContent) {
                alertHistoryContent.innerHTML = `
                    <p class="error-state">
                        Não foi possível carregar o sistema de alertas.
                    </p>
                `;
            }
        }
    } catch (error) {
        if (selectedSensorId !== sensorId) {
            return;
        }

        console.error("Erro ao carregar detalhes do sensor:", error);

        const alertHistoryContent = document.getElementById(
            "alert-history-content"
        );

        if (alertHistoryContent) {
            alertHistoryContent.innerHTML = `
                <p class="error-state">
                    Não foi possível carregar os dados deste sensor.
                </p>
            `;
        }
    }
}

async function refreshSelectedSensorDetails(sensorId) {
    if (selectedSensorId !== sensorId) {
        return;
    }

    try {
        const [history, predictions] = await Promise.all([
            fetchHistory(sensorId),
            fetchPredictions(sensorId),
        ]);

        if (selectedSensorId !== sensorId) {
            return;
        }

        createHistoryChart(history);
        createPredictionChart(predictions);

        lastDetailRefreshAt = Date.now();
        lastDetailHourKey = getCurrentHourKey();
    } catch (error) {
        console.error(
            "Erro ao atualizar histórico/previsões:",
            error
        );
    }
}

async function loadSensors() {
    try {
        const response = await fetch("/api/sensors", {
            credentials: "same-origin",
            cache: "no-store",
        });

        if (response.status === 401) {
            redirectToLogin();
            return false;
        }

        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }

        sensors = await response.json();
        sensorMap.renderSensors(sensors);

        if (!sensors.length) {
            selectedSensorId = null;
            window.selectedSensorId = null;
            lastDetailRefreshAt = 0;
            lastDetailHourKey = null;
            destroyCharts();
            sensorsContainer.innerHTML = `
                <div class="empty-state-block">
                    <p>Nenhum sensor está vinculado à sua conta.</p>
                    <span>Vincule um sensor ao seu usuário no banco de dados para começar o monitoramento.</span>
                </div>
            `;
        } else if (selectedSensorId !== null) {
            const selectedSensor = sensors.find(
                (sensor) => sensor.sensor_id === selectedSensorId
            );

            if (selectedSensor) {
                updateSelectedSensorSummary(selectedSensor);

                try {
                    await refreshAlertState(selectedSensorId);
                } catch (alertError) {
                    console.error(
                        "Erro ao atualizar estado do alerta:",
                        alertError
                    );
                }

                if (shouldRefreshSensorDetails()) {
                    await refreshSelectedSensorDetails(selectedSensorId);
                }
            } else {
                selectedSensorId = null;
                window.selectedSensorId = null;
                lastDetailRefreshAt = 0;
                lastDetailHourKey = null;
                destroyCharts();
                sensorsContainer.innerHTML = `
                    <p class="loading">
                        O sensor selecionado não está mais disponível.
                    </p>
                `;
            }
        }

        connectionIndicator.dataset.state = "connected";
        connectionText.textContent = "Conectado";
        return true;
    } catch (error) {
        console.error("Erro ao carregar sensores:", error);

        connectionIndicator.dataset.state = "error";
        connectionText.textContent = "Erro de conexão";
        return false;
    }
}

async function updateSensors() {
    const loaded = await loadSensors();

    if (loaded) {
        setTimeout(updateSensors, SENSOR_REFRESH_INTERVAL_MS);
    }
}

async function initializeDashboard() {
    try {
        const user = await getCurrentUser();

        if (!user) {
            return;
        }

        currentUserName.textContent = user.name;

        if (adminPanelButton) {
            adminPanelButton.classList.toggle("hidden", user.role !== "admin");
        }

        sensorMap = new SensorMap("sensor-map");

        sensorMap.container.addEventListener(
            "sensor-selected",
            (event) => {
                const sensorId = event.detail.sensorId;

                loadSensorDetails(sensorId).catch((error) => {
                    console.error(
                        "Erro ao carregar detalhes do sensor:",
                        error
                    );
                });
            }
        );

        logoutButton.addEventListener("click", logout);

        const loaded = await loadSensors();

        if (!loaded) {
            return;
        }

        setTimeout(updateSensors, SENSOR_REFRESH_INTERVAL_MS);
    } catch (error) {
        console.error("Erro ao inicializar o dashboard:", error);

        connectionIndicator.dataset.state = "error";
        connectionText.textContent = "Erro de autenticação";
    }
}

initializeDashboard();
