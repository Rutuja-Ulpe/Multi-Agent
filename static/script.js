/* =========================================================
   TRIPMATE AI - SCRIPT.JS
========================================================= */


/* =========================================================
   GLOBAL VARIABLES
========================================================= */

let currentThreadId =
    localStorage.getItem("travel_thread_id") || null;

let latestAnswerMarkdown = "";


/* =========================================================
   SET QUICK PROMPT
========================================================= */

function setPrompt(text) {

    const input =
        document.getElementById("userInput");

    if (!input) {
        console.error("Input box not found.");
        return;
    }

    // Put selected prompt into textarea
    input.value = text;

    // Focus textarea
    input.focus();

    // Automatically generate travel plan
    setTimeout(() => {
        sendMessage();
    }, 100);
}


/* =========================================================
   SET LOADING STATE
========================================================= */

function setLoading(isLoading) {

    const sendBtn =
        document.getElementById("sendBtn");

    const btnText =
        document.getElementById("btnText");

    const btnLoader =
        document.getElementById("btnLoader");

    if (!sendBtn) {
        return;
    }

    sendBtn.disabled = isLoading;

    if (isLoading) {

        if (btnText) {
            btnText.classList.add("hidden");
        }

        if (btnLoader) {
            btnLoader.classList.remove("hidden");
        }

    } else {

        if (btnText) {
            btnText.classList.remove("hidden");
        }

        if (btnLoader) {
            btnLoader.classList.add("hidden");
        }
    }
}


/* =========================================================
   SHOW ERROR
========================================================= */

function showError(message) {

    const errorBox =
        document.getElementById("errorBox");

    if (!errorBox) {
        console.error(message);
        return;
    }

    errorBox.textContent = message;

    errorBox.classList.remove("hidden");

    errorBox.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });
}


/* =========================================================
   HIDE ERROR
========================================================= */

function hideError() {

    const errorBox =
        document.getElementById("errorBox");

    if (!errorBox) {
        return;
    }

    errorBox.classList.add("hidden");

    errorBox.textContent = "";
}


/* =========================================================
   CLEAN MARKDOWN TEXT
========================================================= */

function cleanMarkdownText(text) {

    if (!text) {
        return "";
    }

    return text
        // Remove markdown headings
        .replace(/^#{1,6}\s*/, "")

        // Remove bold
        .replace(/\*\*(.*?)\*\*/g, "$1")

        // Remove italic
        .replace(/\*(.*?)\*/g, "$1")

        .trim();
}


/* =========================================================
   EXTRACT TRIP TITLE
========================================================= */

function extractTripTitle(answer) {

    if (!answer) {
        return "AI Travel Plan";
    }

    const lines =
        answer.split("\n");

    for (let i = 0; i < lines.length; i++) {

        const originalLine =
            lines[i].trim();

        if (!originalLine) {
            continue;
        }

        const cleanLine =
            cleanMarkdownText(originalLine);

        if (!cleanLine) {
            continue;
        }

        const lower =
            cleanLine.toLowerCase();


        // Ignore generic headings

        if (
            lower === "ai travel plan" ||
            lower === "your ai travel plan" ||
            lower === "travel plan"
        ) {
            continue;
        }


        // Ignore numbered sections

        if (
            /^\d+\.\s+/.test(cleanLine)
        ) {
            continue;
        }


        // First useful line = trip title

        return cleanLine;
    }

    return "AI Travel Plan";
}


/* =========================================================
   SHOW RESULT
========================================================= */

function showResult(answer, threadId) {

    /*
     * Store COMPLETE answer.
     */

    latestAnswerMarkdown =
        answer || "";


    /*
     * Get HTML elements.
     */

    const resultSection =
        document.getElementById(
            "resultSection"
        );

    const resultBox =
        document.getElementById(
            "resultBox"
        );

    const tripTitle =
        document.getElementById(
            "tripTitle"
        );

    const threadInfo =
        document.getElementById(
            "threadInfo"
        );


    /*
     * Validate elements.
     */

    if (
        !resultSection ||
        !resultBox ||
        !tripTitle ||
        !threadInfo
    ) {

        console.error(
            "Result elements not found."
        );

        return;
    }


    /* =====================================================
       DISPLAY TITLE
    ===================================================== */

    tripTitle.innerHTML = "";

    const titleElement =
        document.createElement("h1");

    titleElement.className =
        "trip-title";

    titleElement.textContent =
        extractTripTitle(answer);

    tripTitle.appendChild(
        titleElement
    );


    /* =====================================================
       DISPLAY COMPLETE BACKEND RESPONSE
    ===================================================== */

    /*
     * IMPORTANT:
     *
     * We DO NOT filter the answer.
     *
     * Whatever backend.py returns inside
     * data.answer will be displayed.
     *
     * Expected sections:
     *
     * 1. Trip Summary
     * 2. Flight Information
     * 3. Hotel Information
     * 4. Weather Information
     * 5. Day-by-Day Itinerary
     * 6. Estimated Budget
     * 7. Travel Recommendations
     */

    if (
        typeof marked !== "undefined"
    ) {

        resultBox.innerHTML =
            marked.parse(
                answer || ""
            );

    } else {

        /*
         * Fallback if marked.js
         * is not loaded.
         */

        resultBox.textContent =
            answer || "";
    }


    /* =====================================================
       DISPLAY THREAD ID
    ===================================================== */

    threadInfo.textContent =
        `Thread ID: ${threadId}`;


    /* =====================================================
       SHOW RESULT
    ===================================================== */

    resultSection.classList.remove(
        "hidden"
    );


    /* =====================================================
       SCROLL TO RESULT
    ===================================================== */

    setTimeout(() => {

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }, 100);
}


/* =========================================================
   SEND MESSAGE
========================================================= */

async function sendMessage() {

    /*
     * Hide previous error.
     */

    hideError();


    /*
     * Get input.
     */

    const input =
        document.getElementById(
            "userInput"
        );


    if (!input) {

        showError(
            "Input box not found."
        );

        return;
    }


    /*
     * Get user message.
     */

    const message =
        input.value.trim();


    /*
     * Validate message.
     */

    if (!message) {

        showError(
            "Please enter your travel request first."
        );

        return;
    }


    /*
     * Start loading.
     */

    setLoading(true);


    try {

        console.log(
            "===================================="
        );

        console.log(
            "SENDING TRAVEL REQUEST"
        );

        console.log(
            message
        );

        console.log(
            "===================================="
        );


        /* =================================================
           CALL FASTAPI BACKEND
        ================================================= */

        const response =
            await fetch(
                "/api/travel",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        message:
                            message,

                        thread_id:
                            currentThreadId

                    })
                }
            );


        /* =================================================
           CONVERT RESPONSE TO JSON
        ================================================= */

        const data =
            await response.json();


        /* =================================================
           DEBUG BACKEND RESPONSE
        ================================================= */

        console.log(
            "===================================="
        );

        console.log(
            "BACKEND RESPONSE"
        );

        console.log(
            data
        );

        console.log(
            "===================================="
        );


        console.log(
            "===================================="
        );

        console.log(
            "COMPLETE BACKEND ANSWER"
        );

        console.log(
            data.answer
        );

        console.log(
            "===================================="
        );


        console.log(
            "ANSWER LENGTH:"
        );

        console.log(
            data.answer
                ? data.answer.length
                : 0
        );


        /* =================================================
           CHECK API ERROR
        ================================================= */

        if (
            !response.ok ||
            !data.success
        ) {

            throw new Error(
                data.error ||
                "Something went wrong while generating the travel plan."
            );
        }


        /* =================================================
           SAVE THREAD ID
        ================================================= */

        currentThreadId =
            data.thread_id;

        if (currentThreadId) {

            localStorage.setItem(
                "travel_thread_id",
                currentThreadId
            );
        }


        /* =================================================
           DISPLAY COMPLETE RESULT
        ================================================= */

        showResult(
            data.answer,
            data.thread_id
        );


        /*
         * Clear input after success.
         */

        input.value = "";


    } catch (error) {

        console.error(
            "===================================="
        );

        console.error(
            "TRAVEL PLANNER ERROR"
        );

        console.error(
            error
        );

        console.error(
            "===================================="
        );


        showError(
            error.message ||
            "Unable to generate travel plan."
        );


    } finally {

        /*
         * Stop loading.
         */

        setLoading(false);
    }
}


/* =========================================================
   COPY RESULT
========================================================= */

function copyResult() {

    const tripTitle =
        document.getElementById(
            "tripTitle"
        );

    const resultBox =
        document.getElementById(
            "resultBox"
        );


    if (
        !tripTitle ||
        !resultBox
    ) {

        showError(
            "Result not found."
        );

        return;
    }


    /*
     * Get visible text.
     */

    const text =
        tripTitle.innerText +
        "\n\n" +
        resultBox.innerText;


    /*
     * Validate.
     */

    if (!text.trim()) {

        showError(
            "No travel plan available to copy."
        );

        return;
    }


    /*
     * Copy result.
     */

    navigator.clipboard
        .writeText(text)

        .then(() => {

            const copyBtn =
                document.querySelector(
                    ".copy-btn"
                );

            if (!copyBtn) {
                return;
            }


            const oldText =
                copyBtn.textContent;


            copyBtn.textContent =
                "Copied!";


            setTimeout(() => {

                copyBtn.textContent =
                    oldText;

            }, 1400);

        })

        .catch((error) => {

            console.error(
                "Copy error:",
                error
            );

            showError(
                "Could not copy result."
            );

        });
}


/* =========================================================
   DOWNLOAD PDF
========================================================= */

function downloadPDF() {

    const pdfContent =
        document.getElementById(
            "pdfContent"
        );


    /*
     * Validate.
     */

    if (
        !latestAnswerMarkdown ||
        !pdfContent
    ) {

        showError(
            "No travel plan available to download."
        );

        return;
    }


    /*
     * Check html2pdf.
     */

    if (
        typeof html2pdf === "undefined"
    ) {

        showError(
            "PDF library is not loaded. Please refresh the page."
        );

        return;
    }


    /*
     * Get download button.
     */

    const downloadBtn =
        document.querySelector(
            ".download-btn"
        );


    if (!downloadBtn) {

        showError(
            "Download button not found."
        );

        return;
    }


    const oldText =
        downloadBtn.textContent;


    /*
     * Loading state.
     */

    downloadBtn.textContent =
        "Preparing PDF...";

    downloadBtn.disabled =
        true;


    /*
     * Save original styles.
     */

    const originalWidth =
        pdfContent.style.width;

    const originalMaxWidth =
        pdfContent.style.maxWidth;

    const originalMargin =
        pdfContent.style.margin;

    const originalPadding =
        pdfContent.style.padding;

    const originalBackground =
        pdfContent.style.background;


    /*
     * Temporary PDF styles.
     */

    pdfContent.style.width =
        "100%";

    pdfContent.style.maxWidth =
        "100%";

    pdfContent.style.margin =
        "0";

    pdfContent.style.padding =
        "0";

    pdfContent.style.background =
        "#ffffff";


    /* =====================================================
       PDF OPTIONS
    ===================================================== */

    const options = {

        margin: [
            0.45,
            0.45,
            0.45,
            0.45
        ],

        filename:
            "tripmate-ai-travel-plan.pdf",

        image: {

            type: "jpeg",

            quality: 0.98
        },

        html2canvas: {

            scale: 2,

            useCORS: true,

            allowTaint: true,

            backgroundColor:
                "#ffffff",

            logging: false,

            scrollX: 0,

            scrollY: 0
        },

        jsPDF: {

            unit: "in",

            format: "a4",

            orientation:
                "portrait",

            compress: true
        },

        /*
         * Do not use "avoid-all".
         */

        pagebreak: {

            mode: [
                "css",
                "legacy"
            ]
        }
    };


    /* =====================================================
       GENERATE PDF
    ===================================================== */

    html2pdf()

        .set(options)

        .from(pdfContent)

        .toPdf()

        .get("pdf")

        .then(function(pdf) {

            console.log(
                "PDF pages:",
                pdf.internal.getNumberOfPages()
            );

        })

        .save()

        .then(function() {

            /*
             * Restore original styles.
             */

            pdfContent.style.width =
                originalWidth;

            pdfContent.style.maxWidth =
                originalMaxWidth;

            pdfContent.style.margin =
                originalMargin;

            pdfContent.style.padding =
                originalPadding;

            pdfContent.style.background =
                originalBackground;


            /*
             * Restore button.
             */

            downloadBtn.textContent =
                oldText;

            downloadBtn.disabled =
                false;

        })

        .catch(function(error) {

            console.error(
                "PDF generation error:",
                error
            );


            /*
             * Restore styles.
             */

            pdfContent.style.width =
                originalWidth;

            pdfContent.style.maxWidth =
                originalMaxWidth;

            pdfContent.style.margin =
                originalMargin;

            pdfContent.style.padding =
                originalPadding;

            pdfContent.style.background =
                originalBackground;


            /*
             * Restore button.
             */

            downloadBtn.textContent =
                oldText;

            downloadBtn.disabled =
                false;


            showError(
                "Could not download PDF. Please try again."
            );

        });
}


/* =========================================================
   CTRL + ENTER
========================================================= */

document.addEventListener(
    "keydown",
    function(event) {

        /*
         * Ctrl + Enter generates
         * travel plan.
         */

        if (
            event.target &&
            event.target.id === "userInput" &&
            event.ctrlKey &&
            event.key === "Enter"
        ) {

            event.preventDefault();

            sendMessage();
        }

    }
);