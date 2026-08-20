const form = document.getElementById("shorten-form");
const input = document.getElementById("url-input");
const result = document.getElementById("result");
const shortUrl = document.getElementById("short-url");
const themeToggle = document.getElementById("theme-toggle");

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const longUrl = input.value;

    try {
        const response = await fetch("/shorten", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                url: longUrl
            })
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.error);
            return;
        }

        shortUrl.href = data.short_url;
        shortUrl.textContent = data.short_url;
        result.classList.remove("hidden");

    } catch (error) {
        alert("Something went wrong.");
    }
});

themeToggle.addEventListener("click", function () {
    document.body.classList.toggle("dark");

    if (document.body.classList.contains("dark")) {
        themeToggle.textContent = "Light Mode";
    } else {
        themeToggle.textContent = "Dark Mode";
    }
});