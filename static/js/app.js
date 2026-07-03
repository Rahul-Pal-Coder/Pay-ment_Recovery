document.addEventListener("DOMContentLoaded", () => {
    const alerts = document.querySelectorAll(".alert");
    alerts.forEach((alertElement) => {
        window.setTimeout(() => {
            const closeButton = alertElement.querySelector(".btn-close");
            if (closeButton) {
                closeButton.click();
            }
        }, 4000);
    });
});




