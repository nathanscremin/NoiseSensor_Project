const notificationEmailElement =
    document.getElementById("notification-email");
const notificationEmailStatusElement =
    document.getElementById("notification-email-status");
const telegramBotUsernameElement =
    document.getElementById("telegram-bot-username");
const telegramLinkButton =
    document.getElementById("telegram-link-button");
const telegramStatusElement =
    document.getElementById("notification-telegram-status");
const telegramMessageElement =
    document.getElementById("notification-telegram-message");

const TELEGRAM_STATUS_REFRESH_INTERVAL_MS = 2000;
let telegramStatusTimer = null;

function showTelegramMessage(text, type = "") {
    if (!telegramMessageElement) {
        return;
    }

    telegramMessageElement.textContent = text;
    telegramMessageElement.className = `form-message ${type}`.trim();
}

function renderNotificationUser(user) {
    if (notificationEmailElement) {
        notificationEmailElement.textContent = user.email;
    }

    if (notificationEmailStatusElement) {
        notificationEmailStatusElement.textContent =
            user.email_verified ? "Verificado" : "Não verificado";
    }

    if (telegramStatusElement) {
        telegramStatusElement.textContent =
            user.telegram_chat_id !== null
                ? "Vinculado"
                : "Não vinculado";
        telegramStatusElement.className =
            `form-message ${
                user.telegram_chat_id !== null
                    ? "success"
                    : ""
            }`.trim();
    }

    if (telegramLinkButton) {
        telegramLinkButton.textContent =
            user.telegram_chat_id !== null
                ? "Vincular outro Telegram"
                : "Vincular Telegram";
    }
}

async function loadNotificationConfig() {
    try {
        const response = await fetch(
            "/api/auth/me",
            {
                credentials: "same-origin",
                cache: "no-store",
            }
        );

        if (response.status === 401) {
            window.location.href = "/login";
            return null;
        }

        if (!response.ok) {
            throw new Error(
                `Erro ao carregar notificações: ${response.status}`
            );
        }

        const user = await response.json();
        renderNotificationUser(user);
        return user;
    } catch (error) {
        console.error(
            "Erro ao carregar configuração de notificações:",
            error
        );

        if (telegramStatusElement) {
            telegramStatusElement.textContent =
                "Erro ao carregar";
        }

        showTelegramMessage(
            "Não foi possível carregar o estado das notificações.",
            "error"
        );

        return null;
    }
}

function startTelegramStatusPolling() {
    if (telegramStatusTimer !== null) {
        clearInterval(telegramStatusTimer);
    }

    telegramStatusTimer = window.setInterval(
        async () => {
            const user = await loadNotificationConfig();

            if (
                user &&
                user.telegram_chat_id !== null
            ) {
                clearInterval(telegramStatusTimer);
                telegramStatusTimer = null;

                showTelegramMessage(
                    "Telegram vinculado com sucesso.",
                    "success"
                );
            }
        },
        TELEGRAM_STATUS_REFRESH_INTERVAL_MS
    );

    window.setTimeout(() => {
        if (telegramStatusTimer !== null) {
            clearInterval(telegramStatusTimer);
            telegramStatusTimer = null;
        }
    }, 60_000);
}

const telegramLinkForm = document.getElementById(
    "telegram-link-form"
);

if (telegramLinkForm) {
    telegramLinkForm.addEventListener(
        "submit",
        () => {
            if (telegramLinkButton) {
                telegramLinkButton.disabled = true;
            }

            showTelegramMessage(
                "Abra o Telegram na nova aba e toque em Iniciar. Depois volte para esta página."
            );

            startTelegramStatusPolling();

            window.setTimeout(() => {
                if (telegramLinkButton) {
                    telegramLinkButton.disabled = false;
                }
            }, 5000);
        }
    );
}

if (
    telegramBotUsernameElement &&
    telegramLinkButton &&
    telegramBotUsernameElement.value === "Não configurado"
) {
    telegramLinkButton.disabled = true;
}

loadNotificationConfig();
