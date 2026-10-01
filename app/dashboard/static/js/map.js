class SensorMap {
    constructor(containerId) {
        this.container =
            document.getElementById(
                containerId
            );

        if (!this.container) {
            throw new Error(
                `Container do mapa não encontrado: ${containerId}`
            );
        }

        this.map =
            L.map(
                this.container
            ).setView(
                [0, 0],
                2
            );

        this.markers =
            new Map();

        this.geoJsonLayer = null;

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution:
                    "&copy; OpenStreetMap contributors"
            }
        ).addTo(
            this.map
        );

        this.loadGeoJson();
    }

    async loadGeoJson() {
        try {
            const response =
                await fetch(
                    "/static/map/santo_andre_dashboard.geojson"
                );

            if (!response.ok) {
                throw new Error(
                    `Erro HTTP: ${response.status}`
                );
            }

            const geoJson =
                await response.json();

            this.geoJsonLayer =
                L.geoJSON(
                    geoJson,
                    {
                        style: {
                            weight: 1,
                            fillOpacity: 0.15
                        }
                    }
                );

            this.geoJsonLayer.addTo(
                this.map
            );

            const bounds =
                this.geoJsonLayer.getBounds();

            if (bounds.isValid()) {
                this.map.fitBounds(
                    bounds
                );
            }

        } catch (error) {
            console.error(
                "Erro ao carregar mapa:",
                error
            );
        }
    }

    renderSensors(sensors) {
        for (
            const marker
            of this.markers.values()
        ) {
            this.map.removeLayer(
                marker
            );
        }

        this.markers.clear();

        for (const sensor of sensors) {
            const marker =
                L.marker(
                    [
                        sensor.latitude,
                        sensor.longitude
                    ]
                );

            marker.bindPopup(`
                <strong>${sensor.name}</strong><br>
                ${sensor.noise_db.toFixed(2)} dB
            `);

            marker.on(
                "click",
                () => {
                    const event =
                        new CustomEvent(
                            "sensor-selected",
                            {
                                detail: {
                                    sensorId:
                                        sensor.sensor_id
                                }
                            }
                        );

                    this.container.dispatchEvent(
                        event
                    );
                }
            );

            marker.addTo(
                this.map
            );

            this.markers.set(
                sensor.sensor_id,
                marker
            );
        }
    }
}
