document.querySelectorAll("[data-source-tab]").forEach(function (tab) {
    tab.addEventListener("click", function () {
        const source = tab.dataset.sourceTab;

        document.querySelectorAll("[data-source-tab]").forEach(function (item) {
            const isActive = item === tab;
            item.classList.toggle("is-active", isActive);
            item.setAttribute("aria-selected", String(isActive));
            item.tabIndex = isActive ? 0 : -1;
        });

        document.querySelectorAll("[data-source-panel]").forEach(function (panel) {
            panel.hidden = panel.dataset.sourcePanel !== source;
        });

        const pasteInput = document.querySelector("[data-paste-input]");
        const fileInput = document.querySelector("[data-file-input]");
        if (pasteInput && fileInput) {
            pasteInput.required = source === "paste";
            fileInput.required = source === "upload";
        }
    });
});

const resumeInput = document.querySelector("[data-paste-input]");
const characterCount = document.querySelector("[data-character-count]");
if (resumeInput && characterCount) {
    resumeInput.addEventListener("input", function () {
        const count = resumeInput.value.length;
        characterCount.textContent = `${count.toLocaleString()} ${count === 1 ? "character" : "characters"}`;
    });
}

const fileInput = document.querySelector("[data-file-input]");
const fileName = document.querySelector("[data-file-name]");
const uploadZone = document.querySelector("[data-upload-zone]");
if (fileInput && fileName && uploadZone) {
    fileInput.addEventListener("change", function () {
        const file = fileInput.files[0];
        fileName.textContent = file ? file.name : "Choose a resume file";
        uploadZone.classList.toggle("has-file", Boolean(file));
    });

    ["dragenter", "dragover"].forEach(function (eventName) {
        uploadZone.addEventListener(eventName, function (event) {
            event.preventDefault();
            uploadZone.classList.add("is-dragging");
        });
    });

    ["dragleave", "dragend"].forEach(function (eventName) {
        uploadZone.addEventListener(eventName, function () {
            uploadZone.classList.remove("is-dragging");
        });
    });

    uploadZone.addEventListener("drop", function (event) {
        event.preventDefault();
        uploadZone.classList.remove("is-dragging");
        if (event.dataTransfer.files.length) {
            fileInput.files = event.dataTransfer.files;
            fileInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
    });
}

const analysisForm = document.querySelector("#analysis-form");
if (analysisForm) {
    analysisForm.addEventListener("submit", function () {
        const submitButton = analysisForm.querySelector(".analyze-button");
        const submitLabel = analysisForm.querySelector("[data-submit-label]");
        if (submitButton && submitLabel) {
            submitButton.disabled = true;
            submitButton.setAttribute("aria-busy", "true");
            submitLabel.textContent = "Building your readout…";
        }
    });
}

const historySearch = document.querySelector("[data-history-search]");
if (historySearch) {
    const historyItems = Array.from(document.querySelectorAll("[data-history-item]"));
    const historyCount = document.querySelector("[data-history-count]");
    const emptyMessage = document.querySelector("[data-history-empty]");
    historySearch.addEventListener("input", function () {
        const query = historySearch.value.trim().toLocaleLowerCase();
        let visibleCount = 0;

        historyItems.forEach(function (item) {
            const matches = item.dataset.search.includes(query);
            item.hidden = !matches;
            visibleCount += Number(matches);
        });

        if (historyCount) {
            historyCount.textContent = `${visibleCount} ${visibleCount === 1 ? "result" : "results"}`;
        }
        if (emptyMessage) {
            emptyMessage.hidden = visibleCount !== 0;
        }
    });
}