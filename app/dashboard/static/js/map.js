class SensorMap {
    constructor(containerId) {
        this.container = document.getElementById(containerId);

        if (!this.container) {
            throw new Error(
                `Container do mapa não encontrado: ${containerId}`
            );
        }

        this.map = L.map(this.container).setView([0, 0], 2);
        this.markers = new Map();
        this.geoJsonLayer = null;

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution: "&copy; OpenStreetMap contributors",
            }
        ).addTo(this.map);

        this.loadGeoJson();
    }

    async loadGeoJson() {
        try {
            const response = await fetch(
                "/static/map/santo_andre_dashboard.geojson"
            );

            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const geoJson = await response.json();

            this.geoJsonLayer = L.geoJSON(geoJson, {
                style: {
                    weight: 1,
                    fillOpacity: 0.15,
                },
            });

            this.geoJsonLayer.addTo(this.map);

            const bounds = this.geoJsonLayer.getBounds();

            if (bounds.isValid()) {
                this.map.fitBounds(bounds, {
                    padding: [20, 20],
                });
            }
        } catch (error) {
            console.error("Erro ao carregar mapa:", error);
        }
    }

    renderSensors(sensors) {
        const sensorIds = new Set(
            sensors.map((sensor) => sensor.sensor_id)
        );

        for (const [sensorId, marker] of this.markers.entries()) {
            if (!sensorIds.has(sensorId)) {
                this.map.removeLayer(marker);
                this.markers.delete(sensorId);
            }
        }

        const alertStateLabels = {
            normal: "Normal",
            pending_alert: "Aguardando ativação",
            alert: "Em alerta",
            pending_recovery: "Aguardando recuperação",
        };

        for (const sensor of sensors) {
            const alertState =
                alertStateLabels[sensor.alert_state] || "Desconhecido";

            const noiseText =
                sensor.noise_db === null || sensor.noise_db === undefined
                    ? "Aguardando primeira leitura"
                    : `${Number(sensor.noise_db).toFixed(2)} dB`;

            const popup = `
                <div style="max-width: 220px; overflow-wrap: anywhere;">
                    <strong>${sensor.name}</strong><br>
                    ${noiseText}<br>
                    Estado do alerta: ${alertState}
                </div>
            `;

            let marker = this.markers.get(sensor.sensor_id);

            if (!marker) {
                marker = L.marker([
                    sensor.latitude,
                    sensor.longitude,
                ]);

                marker.on("click", () => {
                    const event = new CustomEvent("sensor-selected", {
                        detail: {
                            sensorId: sensor.sensor_id,
                        },
                    });

                    this.container.dispatchEvent(event);
                });

                marker.addTo(this.map);
                this.markers.set(sensor.sensor_id, marker);
            } else {
                marker.setLatLng([
                    sensor.latitude,
                    sensor.longitude,
                ]);
            }

            marker.bindPopup(popup);
        }
    }
}
