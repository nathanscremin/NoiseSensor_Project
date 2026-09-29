const sensorsContainer = document.getElementById(
    "sensors-container"
);

const connectionIndicator = document.getElementById(
    "connection-indicator"
);

const connectionText = document.getElementById(
    "connection-text"
);


function formatTimestamp(timestamp) {
    const date = new Date(timestamp);

    return date.toLocaleString("pt-BR");
}


function formatChartTime(timestamp) {
    const date = new Date(timestamp);

    return date.toLocaleTimeString(
        "pt-BR",
        {
            hour: "2-digit",
            minute: "2-digit",
        }
    );
}


async function fetchHistory(sensorId) {
    const response = await fetch(
        `/api/sensors/${sensorId}/history`
    );

    if (!response.ok) {
        throw new Error(
            `Erro ao buscar histórico: ${response.status}`
        );
    }

    return response.json();
}


async function fetchPredictions(sensorId) {
    const response = await fetch(
        `/api/sensors/${sensorId}/predictions`
    );

    if (!response.ok) {
        throw new Error(
            `Erro ao buscar previsões: ${response.status}`
        );
    }

    return response.json();
}


function createHistoryChart(
    canvas,
    history
) {
    const labels = history.map(
        item => formatChartTime(item.timestamp)
    );

    const values = history.map(
        item => item.avg_noise_db
    );

    return new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels: labels,

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

                scales: {
                    y: {
                        title: {
                            display: true,
                            text: "dB",
                        },
                    },
                },
            },
        }
    );
}


function createPredictionChart(
    canvas,
    predictions
) {
    const labels = predictions.map(
        item => formatChartTime(item.timestamp)
    );

    const values = predictions.map(
        item => item.predicted_noise_db
    );

    return new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels: labels,

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

                scales: {
                    y: {
                        title: {
                            display: true,
                            text: "dB",
                        },
                    },
                },
            },
        }
    );
}


async function createSensorCharts(
    sensor,
    historyCanvas,
    predictionCanvas
) {
    const [
        history,
        predictions,
    ] = await Promise.all([
        fetchHistory(sensor.sensor_id),
        fetchPredictions(sensor.sensor_id),
    ]);

    createHistoryChart(
        historyCanvas,
        history
    );

    createPredictionChart(
        predictionCanvas,
        predictions
    );
}


function renderSensors(sensors) {
    sensorsContainer.innerHTML = "";

    if (sensors.length === 0) {
        sensorsContainer.innerHTML = `
            <p class="loading">
                Nenhum sensor encontrado.
            </p>
        `;

        return;
    }

    for (const sensor of sensors) {
        const card = document.createElement("article");

        card.className = "sensor-card";

        card.innerHTML = `
            <div class="sensor-header">
                <div>
                    <h3 class="sensor-name">
                        ${sensor.name}
                    </h3>

                    <p class="sensor-region">
                        Região: ${sensor.region}
                    </p>
                </div>

                <div class="sensor-noise">
                    ${sensor.noise_db.toFixed(2)} dB
                </div>
            </div>

            <span class="sensor-status">
                ${sensor.status}
            </span>

            <div class="sensor-footer">
                Última coleta:
                ${formatTimestamp(sensor.read_timestamp)}
            </div>

            <div class="sensor-charts">

                <section class="chart-section">
                    <h4>
                        Histórico — últimas 24 horas
                    </h4>

                    <div class="chart-container">
                        <canvas
                            class="history-chart"
                        ></canvas>
                    </div>
                </section>

                <section class="chart-section">
                    <h4>
                        Previsão — próximas 24 horas
                    </h4>

                    <div class="chart-container">
                        <canvas
                            class="prediction-chart"
                        ></canvas>
                    </div>
                </section>

            </div>
        `;

        sensorsContainer.appendChild(card);

        const historyCanvas =
            card.querySelector(".history-chart");

        const predictionCanvas =
            card.querySelector(".prediction-chart");

        createSensorCharts(
            sensor,
            historyCanvas,
            predictionCanvas
        ).catch(error => {
            console.error(
                `Erro nos gráficos do sensor ${sensor.sensor_id}:`,
                error
            );
        });
    }
}


async function loadSensors() {
    try {
        const response = await fetch(
            "/api/sensors"
        );

        if (!response.ok) {
            throw new Error(
                `Erro HTTP: ${response.status}`
            );
        }

        const sensors = await response.json();

        renderSensors(sensors);

        connectionIndicator.style.background = "#12b76a";

        connectionText.textContent =
            "Conectado";

    } catch (error) {
        console.error(
            "Erro ao carregar sensores:",
            error
        );

        connectionIndicator.style.background =
            "#f04438";

        connectionText.textContent =
            "Erro de conexão";
    }
}


async function updateSensors() {
    await loadSensors();

    setTimeout(
        updateSensors,
        10000
    );
}


updateSensors();
