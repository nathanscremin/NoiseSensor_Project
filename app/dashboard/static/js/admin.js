const usersTableBody = document.getElementById("users-table-body");
const auditTableBody = document.getElementById("audit-table-body");
const assignmentUser = document.getElementById("assignment-user");
const assignmentSensorList = document.getElementById("assignment-sensor-list");
const assignmentUserHelp = document.getElementById("assignment-user-help");
const saveAssignmentsButton = document.getElementById("save-assignments-button");
const assignmentMessage = document.getElementById("assignment-message");
const adminMessage = document.getElementById("admin-message");
const logoutButton = document.getElementById("admin-logout-button");

const statUserCount = document.getElementById("stat-user-count");
const statAdminCount = document.getElementById("stat-admin-count");
const statSensorCount = document.getElementById("stat-sensor-count");
const statUnassignedSensorCount = document.getElementById("stat-unassigned-sensor-count");

let users = [];
let sensors = [];
let currentUser = null;

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatDate(timestamp) {
    const date = new Date(timestamp);

    if (Number.isNaN(date.getTime())) {
        return "Data indisponível";
    }

    return date.toLocaleString("pt-BR");
}

function showAdminMessage(message, state = "success") {
    adminMessage.textContent = message;
    adminMessage.dataset.state = state;
    adminMessage.classList.remove("hidden");
}

function clearInlineMessage(element) {
    element.textContent = "";
    delete element.dataset.state;
}

function setInlineMessage(element, message, state = "success") {
    element.textContent = message;
    element.dataset.state = state;
}

async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Sessão expirada.");
    }

    if (response.status === 403) {
        window.location.href = "/";
        throw new Error("Acesso administrativo negado.");
    }

    if (!response.ok) {
        let detail = `Erro HTTP ${response.status}`;

        try {
            const payload = await response.json();
            if (payload.detail) {
                detail = payload.detail;
            }
        } catch (_error) {
            // Mantém a mensagem HTTP padrão.
        }

        throw new Error(detail);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

async function loadOverview() {
    const overview = await apiFetch("/api/admin/overview");

    statUserCount.textContent = overview.user_count;
    statAdminCount.textContent = overview.admin_count;
    statSensorCount.textContent = overview.sensor_count;
    statUnassignedSensorCount.textContent = overview.unassigned_sensor_count;
}

function renderUsers() {
    if (!users.length) {
        usersTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="admin-empty-state">
                    Nenhum usuário encontrado.
                </td>
            </tr>
        `;
        return;
    }

    usersTableBody.innerHTML = users.map((user) => {
        const isSelf = currentUser && user.user_id === currentUser.user_id;
        const roleLabel = user.role === "admin" ? "Admin" : "Usuário";
        const verified = user.email_verified
            ? '<span class="admin-badge success">Verificado</span>'
            : '<span class="admin-badge warning">Pendente</span>';

        return `
            <tr>
                <td>
                    <span class="admin-user-name">${escapeHtml(user.name)}</span>
                    <span class="admin-user-id">ID ${user.user_id}</span>
                </td>
                <td>${escapeHtml(user.email)}</td>
                <td>${verified}</td>
                <td>
                    <span class="admin-badge ${user.role === "admin" ? "admin" : ""}">
                        ${roleLabel}
                    </span>
                </td>
                <td>${user.sensor_count}</td>
                <td>
                    <select
                        class="admin-role-select"
                        data-user-role="${user.user_id}"
                        ${isSelf ? "disabled" : ""}
                        aria-label="Alterar cargo de ${escapeHtml(user.name)}"
                    >
                        <option value="user" ${user.role === "user" ? "selected" : ""}>Usuário</option>
                        <option value="admin" ${user.role === "admin" ? "selected" : ""}>Admin</option>
                    </select>
                </td>
            </tr>
        `;
    }).join("");

    document.querySelectorAll("[data-user-role]").forEach((select) => {
        select.addEventListener("change", () => {
            changeUserRole(Number(select.dataset.userRole), select.value, select);
        });
    });
}

function renderUserOptions() {
    const selectedValue = assignmentUser.value;

    assignmentUser.innerHTML = '<option value="">Selecione um usuário</option>';

    for (const user of users) {
        const option = document.createElement("option");
        option.value = user.user_id;
        option.textContent = `${user.name} — ${user.email}`;
        assignmentUser.appendChild(option);
    }

    if (users.some((user) => String(user.user_id) === selectedValue)) {
        assignmentUser.value = selectedValue;
    } else {
        assignmentUser.value = "";
    }
}

function renderSensorAssignments(selectedUserId, assignedSensorIds = []) {
    if (!selectedUserId) {
        assignmentSensorList.innerHTML = '<p class="admin-empty-state">Selecione um usuário.</p>';
        saveAssignmentsButton.disabled = true;
        assignmentUserHelp.textContent = "Escolha um usuário para editar suas associações.";
        return;
    }

    const selectedUser = users.find(
        (user) => user.user_id === Number(selectedUserId)
    );

    assignmentUserHelp.textContent = selectedUser
        ? `${selectedUser.name} possui ${selectedUser.sensor_count} sensor(es) associado(s).`
        : "Usuário selecionado.";

    if (!sensors.length) {
        assignmentSensorList.innerHTML = '<p class="admin-empty-state">Nenhum sensor cadastrado.</p>';
        saveAssignmentsButton.disabled = true;
        return;
    }

    const assigned = new Set(assignedSensorIds.map(Number));

    assignmentSensorList.innerHTML = sensors.map((sensor) => `
        <label class="sensor-checkbox-item">
            <input
                type="checkbox"
                value="${sensor.sensor_id}"
                ${assigned.has(sensor.sensor_id) ? "checked" : ""}
            >
            <span class="sensor-checkbox-content">
                <span class="sensor-checkbox-name">${escapeHtml(sensor.name)}</span>
                <span class="sensor-checkbox-meta">
                    ID ${sensor.sensor_id} · ${escapeHtml(sensor.region)} · ${escapeHtml(sensor.status)}
                </span>
            </span>
        </label>
    `).join("");

    saveAssignmentsButton.disabled = false;
}

async function loadUsers() {
    users = await apiFetch("/api/admin/users");
    renderUsers();
    renderUserOptions();
}

async function loadSensors() {
    sensors = await apiFetch("/api/admin/sensors");

    if (assignmentUser.value) {
        const currentSensors = sensors
            .filter((sensor) => sensor.user_ids.includes(Number(assignmentUser.value)))
            .map((sensor) => sensor.sensor_id);

        renderSensorAssignments(assignmentUser.value, currentSensors);
    }
}

async function loadAudit() {
    const audit = await apiFetch("/api/admin/audit?limit=50");

    if (!audit.length) {
        auditTableBody.innerHTML = `
            <tr>
                <td colspan="4" class="admin-empty-state">
                    Ainda não há ações administrativas registradas.
                </td>
            </tr>
        `;
        return;
    }

    auditTableBody.innerHTML = audit.map((item) => `
        <tr>
            <td>${escapeHtml(formatDate(item.created_at))}</td>
            <td>${escapeHtml(item.admin_name)}</td>
            <td>${escapeHtml(item.action)}</td>
            <td>${escapeHtml(item.details)}</td>
        </tr>
    `).join("");
}

async function changeUserRole(userId, role, selectElement) {
    const user = users.find((item) => item.user_id === userId);

    if (!user) {
        return;
    }

    const previousRole = user.role;
    selectElement.disabled = true;
    clearInlineMessage(assignmentMessage);

    try {
        await apiFetch(`/api/admin/users/${userId}/role`, {
            method: "PATCH",
            body: JSON.stringify({ role }),
        });

        showAdminMessage(
            `Cargo de ${user.name} alterado para ${role === "admin" ? "admin" : "usuário"}.`
        );

        await Promise.all([
            loadOverview(),
            loadUsers(),
            loadAudit(),
        ]);
    } catch (error) {
        selectElement.value = previousRole;
        showAdminMessage(error.message, "error");
    } finally {
        selectElement.disabled = userId === currentUser?.user_id;
    }
}

async function loadUserAssignments(userId) {
    clearInlineMessage(assignmentMessage);

    if (!userId) {
        renderSensorAssignments(null, []);
        return;
    }

    try {
        const result = await apiFetch(`/api/admin/users/${userId}/sensors`);
        renderSensorAssignments(userId, result.sensor_ids);
    } catch (error) {
        renderSensorAssignments(userId, []);
        setInlineMessage(assignmentMessage, error.message, "error");
    }
}

async function saveUserAssignments() {
    const userId = Number(assignmentUser.value);

    if (!userId) {
        return;
    }

    const sensorIds = Array.from(
        assignmentSensorList.querySelectorAll('input[type="checkbox"]:checked')
    ).map((input) => Number(input.value));

    saveAssignmentsButton.disabled = true;
    clearInlineMessage(assignmentMessage);

    try {
        await apiFetch(`/api/admin/users/${userId}/sensors`, {
            method: "PUT",
            body: JSON.stringify({ sensor_ids: sensorIds }),
        });

        setInlineMessage(
            assignmentMessage,
            "Associações salvas com sucesso.",
            "success"
        );

        await Promise.all([
            loadOverview(),
            loadUsers(),
            loadSensors(),
            loadAudit(),
        ]);
    } catch (error) {
        setInlineMessage(assignmentMessage, error.message, "error");
    } finally {
        saveAssignmentsButton.disabled = false;
    }
}

async function logout() {
    logoutButton.disabled = true;

    try {
        const response = await fetch("/api/auth/logout", {
            method: "POST",
            credentials: "same-origin",
        });

        if (!response.ok && response.status !== 401) {
            throw new Error(`Erro ao encerrar sessão: ${response.status}`);
        }
    } catch (error) {
        console.error(error);
    } finally {
        window.location.href = "/login";
    }
}

async function initializeAdmin() {
    try {
        currentUser = await apiFetch("/api/auth/me");

        if (currentUser.role !== "admin") {
            window.location.href = "/";
            return;
        }

        await Promise.all([
            loadOverview(),
            loadUsers(),
            loadSensors(),
            loadAudit(),
        ]);
    } catch (error) {
        if (!error.message.includes("Acesso administrativo negado")) {
            showAdminMessage(error.message, "error");
        }
    }
}

assignmentUser.addEventListener("change", () => {
    loadUserAssignments(Number(assignmentUser.value));
});

saveAssignmentsButton.addEventListener("click", saveUserAssignments);
logoutButton.addEventListener("click", logout);

initializeAdmin();
