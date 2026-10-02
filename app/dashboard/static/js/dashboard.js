const sensorsContainer =
    document.getElementById(
        "sensor-details"
    );

const connectionIndicator =
    document.getElementById(
        "connection-indicator"
    );

const connectionText =
    document.getElementById(
        "connection-text"
    );

const currentUserName =
    document.getElementById(
        "current-user-name"
    );

const logoutButton =
    document.getElementById(
        "logout-button"
    );


let sensors = [];

let selectedSensorId =
    null;

let historyChart =
    null;

let predictionChart =
    null;

let sensorMap =
    null;


function redirectToLogin() {
    window.location.href =
        "/login";
}


async function getCurrentUser() {

    const response =
        await fetch(
            "/api/auth/me",
            {
                method: "GET",

                credentials:
                    "same-origin",
            }
        );


    if (
        response.status ===
        401
    ) {

        redirectToLogin();

        return null;
    }


    if (
        !response.ok
    ) {

        throw new Error(
            `Erro ao verificar autenticação: ${response.status}`
        );
    }


    return response.json();
}


async function logout() {

    logoutButton.disabled =
        true;


    try {

        const response =
            await fetch(
                "/api/auth/logout",
                {
                    method: "POST",

                    credentials:
                        "same-origin",
                }
            );


        if (
            !response.ok &&
            response.status !==
            401
        ) {

            throw new Error(
                `Erro ao encerrar sessão: ${response.status}`
            );
        }

    } catch (error) {

        console.error(
            "Erro durante o logout:",
            error
        );

    } finally {

        redirectToLogin();
    }
}


function formatTimestamp(
    timestamp
) {

    const date =
        new Date(timestamp);


    return date.toLocaleString(
        "pt-BR"
    );
}


function formatChartTime(
    timestamp
) {

    const date =
        new Date(timestamp);


    return date.toLocaleTimeString(
        "pt-BR",
        {
            hour:
                "2-digit",

            minute:
                "2-digit",
        }
    );
}


async function fetchHistory(
    sensorId
) {

    const response =
        await fetch(
            `/api/sensors/${sensorId}/history`,
            {
                credentials:
                    "same-origin",
            }
        );


    if (
        response.status ===
        401
    ) {

        redirectToLogin();

        throw new Error(
            "Sessão expirada."
        );
    }


    if (
        !response.ok
    ) {

        throw new Error(
            `Erro ao carregar histórico: ${response.status}`
        );
    }


    return response.json();
}


async function fetchPredictions(
    sensorId
) {

    const response =
        await fetch(
            `/api/sensors/${sensorId}/predictions`,
            {
                credentials:
                    "same-origin",
            }
        );


    if (
        response.status ===
        401
    ) {

        redirectToLogin();

        throw new Error(
            "Sessão expirada."
        );
    }


    if (
        !response.ok
    ) {

        throw new Error(
            `Erro ao carregar previsões: ${response.status}`
        );
    }


    return response.json();
}


function destroyCharts() {

    if (
        historyChart
    ) {

        historyChart.destroy();

        historyChart =
            null;
    }


    if (
        predictionChart
    ) {

        predictionChart.destroy();

        predictionChart =
            null;
    }
}


function renderSensorDetails(
    sensor
) {

    sensorsContainer.innerHTML = `
        <article class="sensor-details-card">

            <div class="sensor-header">

                <div>

                    <h2
                        id="selected-sensor-name"
                        class="sensor-name"
                    >
                        ${sensor.name}
                    </h2>

                    <p
                        id="selected-sensor-region"
                        class="sensor-region"
                    >
                        Região: ${sensor.region}
                    </p>

                </div>

                <div
                    id="selected-sensor-noise"
                    class="sensor-noise"
                >
                    ${sensor.noise_db.toFixed(2)}
                    dB
                </div>

            </div>


            <span
                id="selected-sensor-status"
                class="sensor-status"
            >
                ${sensor.status}
            </span>


            <div class="sensor-footer">

                Última coleta:

                <span
                    id="selected-sensor-timestamp"
                >
                    ${formatTimestamp(
        sensor.read_timestamp
    )}
                </span>

            </div>

        </article>


        <section class="chart-section">

            <h3>
                Histórico — últimas 24 horas
            </h3>

            <div class="chart-container">

                <canvas
                    id="history-chart"
                ></canvas>

            </div>

        </section>


        <section class="chart-section">

            <h3>
                Previsão — próximas 24 horas
            </h3>

            <div class="chart-container">

                <canvas
                    id="prediction-chart"
                ></canvas>

            </div>

        </section>
    `;
}


function updateSelectedSensorSummary(
    sensor
) {

    const nameElement =
        document.getElementById(
            "selected-sensor-name"
        );

    const regionElement =
        document.getElementById(
            "selected-sensor-region"
        );

    const noiseElement =
        document.getElementById(
            "selected-sensor-noise"
        );

    const statusElement =
        document.getElementById(
            "selected-sensor-status"
        );

    const timestampElement =
        document.getElementById(
            "selected-sensor-timestamp"
        );


    if (
        !nameElement ||
        !regionElement ||
        !noiseElement ||
        !statusElement ||
        !timestampElement
    ) {

        return;
    }


    nameElement.textContent =
        sensor.name;

    regionElement.textContent =
        `Região: ${sensor.region}`;

    noiseElement.textContent =
        `${sensor.noise_db.toFixed(2)} dB`;

    statusElement.textContent =
        sensor.status;

    timestampElement.textContent =
        formatTimestamp(
            sensor.read_timestamp
        );
}


function createHistoryChart(
    history
) {

    const canvas =
        document.getElementById(
            "history-chart"
        );


    if (!canvas) {

        return;
    }


    const labels =
        history.map(
            (item) =>
                formatChartTime(
                    item.timestamp
                )
        );


    const values =
        history.map(
            (item) =>
                item.avg_noise_db
        );


    historyChart =
        new Chart(
            canvas,
            {
                type:
                    "line",

                data: {

                    labels,

                    datasets: [

                        {
                            label:
                                "Ruído médio",

                            data:
                                values,

                            tension:
                                0.3,

                            borderWidth:
                                2,

                            pointRadius:
                                3,
                        },
                    ],
                },

                options: {

                    responsive:
                        true,

                    maintainAspectRatio:
                        false,

                    scales: {

                        y: {

                            title: {

                                display:
                                    true,

                                text:
                                    "dB",
                            },
                        },
                    },
                },
            }
        );
}


function createPredictionChart(
    predictions
) {

    const canvas =
        document.getElementById(
            "prediction-chart"
        );


    if (!canvas) {

        return;
    }


    const labels =
        predictions.map(
            (item) =>
                formatChartTime(
                    item.timestamp
                )
        );


    const values =
        predictions.map(
            (item) =>
                item.predicted_noise_db
        );


    predictionChart =
        new Chart(
            canvas,
            {
                type:
                    "line",

                data: {

                    labels,

                    datasets: [

                        {
                            label:
                                "Previsão",

                            data:
                                values,

                            tension:
                                0.3,

                            borderWidth:
                                2,

                            pointRadius:
                                3,
                        },
                    ],
                },

                options: {

                    responsive:
                        true,

                    maintainAspectRatio:
                        false,

                    scales: {

                        y: {

                            title: {

                                display:
                                    true,

                                text:
                                    "dB",
                            },
                        },
                    },
                },
            }
        );
}


async function loadSensorDetails(
    sensorId
) {

    const sensor =
        sensors.find(
            (item) =>
                item.sensor_id ===
                sensorId
        );


    if (!sensor) {

        return;
    }


    selectedSensorId =
        sensorId;


    destroyCharts();


    renderSensorDetails(
        sensor
    );


    const [
        history,
        predictions,
    ] = await Promise.all(
        [
            fetchHistory(
                sensorId
            ),

            fetchPredictions(
                sensorId
            ),
        ]
    );


    /*
     * Impede que uma resposta antiga
     * de outro sensor sobrescreva
     * a seleção atual.
     */

    if (
        selectedSensorId !==
        sensorId
    ) {

        return;
    }


    if (
        history.length > 0
    ) {

        createHistoryChart(
            history
        );
    }


    if (
        predictions.length > 0
    ) {

        createPredictionChart(
            predictions
        );
    }
}


async function loadSensors() {

    try {

        const response =
            await fetch(
                "/api/sensors",
                {
                    credentials:
                        "same-origin",
                }
            );


        if (
            response.status ===
            401
        ) {

            redirectToLogin();

            return false;
        }


        if (
            !response.ok
        ) {

            throw new Error(
                `Erro HTTP: ${response.status}`
            );
        }


        sensors =
            await response.json();


        /*
         * Atualiza os sensores
         * exibidos no mapa.
         */

        sensorMap.renderSensors(
            sensors
        );


        /*
         * Atualiza somente os dados
         * do sensor selecionado.
         *
         * Não recria o HTML dos gráficos,
         * para preservar as instâncias
         * do Chart.js.
         */

        if (
            selectedSensorId !==
            null
        ) {

            const selectedSensor =
                sensors.find(
                    (sensor) =>
                        sensor.sensor_id ===
                        selectedSensorId
                );


            if (
                selectedSensor
            ) {

                updateSelectedSensorSummary(
                    selectedSensor
                );
            }
        }


        connectionIndicator.style.background =
            "#12b76a";

        connectionText.textContent =
            "Conectado";


        return true;

    } catch (error) {

        console.error(
            "Erro ao carregar sensores:",
            error
        );


        connectionIndicator.style.background =
            "#f04438";

        connectionText.textContent =
            "Erro de conexão";


        return false;
    }
}


async function updateSensors() {

    const loaded =
        await loadSensors();


    if (!loaded) {

        return;
    }


    setTimeout(
        updateSensors,
        10000
    );
}


async function initializeDashboard() {

    try {

        const user =
            await getCurrentUser();


        if (!user) {

            return;
        }


        currentUserName.textContent =
            user.name;


        sensorMap =
            new SensorMap(
                "sensor-map"
            );


        sensorMap.container.addEventListener(
            "sensor-selected",
            (event) => {

                const sensorId =
                    event.detail.sensorId;


                loadSensorDetails(
                    sensorId
                ).catch(
                    (error) => {

                        console.error(
                            "Erro ao carregar detalhes do sensor:",
                            error
                        );

                    }
                );

            }
        );


        logoutButton.addEventListener(
            "click",
            logout
        );


        const loaded =
            await loadSensors();


        if (!loaded) {

            return;
        }


        setTimeout(
            updateSensors,
            10000
        );

    } catch (error) {

        console.error(
            "Erro ao inicializar o dashboard:",
            error
        );


        connectionIndicator.style.background =
            "#f04438";

        connectionText.textContent =
            "Erro de autenticação";
    }
}


initializeDashboard();
