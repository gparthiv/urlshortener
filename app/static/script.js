const form = document.getElementById("shorten-form");

const input = document.getElementById("url-input");
const shortenButton = document.getElementById("shorten-button");

const result = document.getElementById("result");
const shortUrl = document.getElementById("short-url");
const openLink = document.getElementById("open-link");

const copyButton = document.getElementById("copy-button");

const loading = document.getElementById("loading");
const error = document.getElementById("error");

const themeToggle = document.getElementById("theme-toggle");



/* -------------------------------- */
/* Shorten URL */
/* -------------------------------- */

form.addEventListener("submit", async function (event) {

    event.preventDefault();

    const longUrl = input.value.trim();


    // Reset previous state

    hideError();

    result.classList.add("hidden");


    if (!longUrl) {
        showError("Please enter a URL.");
        return;
    }


    // Loading state

    loading.classList.remove("hidden");

    shortenButton.disabled = true;
    shortenButton.textContent = "Shortening...";


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

            /*
             * This handles:
             *
             * 400 → invalid URL
             * 429 → rate limit exceeded
             * other backend errors
             */

            throw new Error(
                data.error || "Unable to shorten URL."
            );

        }


        // Display shortened URL

        shortUrl.value = data.short_url;

        openLink.href = data.short_url;

        result.classList.remove("hidden");


    } catch (err) {

        showError(err.message);

    } finally {

        loading.classList.add("hidden");

        shortenButton.disabled = false;
        shortenButton.textContent = "Shorten URL";

    }

});



/* -------------------------------- */
/* Copy shortened URL */
/* -------------------------------- */

copyButton.addEventListener("click", async function () {

    try {

        await navigator.clipboard.writeText(
            shortUrl.value
        );


        const originalText = copyButton.textContent;

        copyButton.textContent = "Copied!";


        setTimeout(function () {

            copyButton.textContent = originalText;

        }, 1500);


    } catch (err) {

        showError(
            "Unable to copy the URL. Please copy it manually."
        );

    }

});



/* -------------------------------- */
/* Dark mode */
/* -------------------------------- */

themeToggle.addEventListener("click", function () {

    document.body.classList.toggle("dark");


    if (document.body.classList.contains("dark")) {

        themeToggle.textContent = "Light Mode";

    } else {

        themeToggle.textContent = "Dark Mode";

    }

});



/* -------------------------------- */
/* Error helpers */
/* -------------------------------- */

function showError(message) {

    error.textContent = message;

    error.classList.remove("hidden");

}


function hideError() {

    error.textContent = "";

    error.classList.add("hidden");

}