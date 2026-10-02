const form =
    document.getElementById(
        "login-form"
    );

const button =
    document.getElementById(
        "login-button"
    );

const message =
    document.getElementById(
        "auth-message"
    );


function showMessage(
    text,
    type = "error"
) {
    message.textContent =
        text;

    message.className =
        `auth-message ${type}`;

    message.hidden =
        false;
}


function getErrorMessage(
    data,
    fallback
) {
    if (
        typeof data?.detail ===
        "string"
    ) {
        return data.detail;
    }

    return fallback;
}


async function redirectAuthenticatedUser() {
    try {
        const response =
            await fetch(
                "/api/auth/me",
                {
                    method: "GET",

                    credentials:
                        "same-origin",
                }
            );

        if (response.ok) {
            window.location.href =
                "/";
        }

    } catch (error) {

        console.error(
            "Erro ao verificar a sessão atual:",
            error
        );

    }
}


function showUrlMessage() {
    const params =
        new URLSearchParams(
            window.location.search
        );

    if (
        params.get("verified") ===
        "1"
    ) {

        showMessage(
            "E-mail verificado com sucesso. Agora você pode entrar.",
            "success"
        );

        return;
    }

    if (
        params.get("registered") ===
        "1"
    ) {

        showMessage(
            "Conta criada. Verifique seu e-mail antes de entrar.",
            "success"
        );
    }
}


form.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();

        const formData =
            new FormData(form);

        const data = {
            email:
                formData.get(
                    "email"
                ),

            password:
                formData.get(
                    "password"
                ),
        };


        button.disabled =
            true;

        message.hidden =
            true;


        try {

            const response =
                await fetch(
                    "/api/auth/login",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        credentials:
                            "same-origin",

                        body:
                            JSON.stringify(
                                data
                            ),
                    }
                );


            const responseData =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    getErrorMessage(
                        responseData,
                        "Não foi possível realizar o login."
                    )
                );
            }


            window.location.href =
                "/";

        } catch (error) {

            console.error(
                "Erro durante o login:",
                error
            );

            showMessage(
                error.message ||
                "Não foi possível realizar o login."
            );

        } finally {

            button.disabled =
                false;
        }
    }
);


showUrlMessage();

redirectAuthenticatedUser();
