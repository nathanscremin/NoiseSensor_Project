const form =
    document.getElementById(
        "register-form"
    );

const button =
    document.getElementById(
        "register-button"
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


form.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        const formData =
            new FormData(form);


        const password =
            formData.get(
                "password"
            );


        const confirmPassword =
            formData.get(
                "confirm_password"
            );


        if (
            password !==
            confirmPassword
        ) {

            showMessage(
                "As senhas não coincidem."
            );

            return;
        }


        const data = {

            name:
                formData.get(
                    "name"
                ),

            email:
                formData.get(
                    "email"
                ),

            password,

            confirm_password:
                confirmPassword,
        };


        button.disabled =
            true;

        message.hidden =
            true;


        try {

            const response =
                await fetch(
                    "/api/auth/register",
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


            if (
                !response.ok
            ) {

                throw new Error(
                    getErrorMessage(
                        responseData,
                        "Não foi possível criar a conta."
                    )
                );
            }


            window.location.href =
                "/login?registered=1";

        } catch (error) {

            console.error(
                "Erro durante o cadastro:",
                error
            );

            showMessage(
                error.message ||
                "Não foi possível criar a conta."
            );

        } finally {

            button.disabled =
                false;
        }
    }
);


redirectAuthenticatedUser();
