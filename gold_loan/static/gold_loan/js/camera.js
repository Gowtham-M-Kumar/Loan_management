(function () {
    let stream = null;
    let facingMode = "environment";
    let currentTargetInputId = null;

    const modal = document.getElementById("cameraModal");
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("cameraCanvas");
    const captureBtn = document.getElementById("cameraCaptureBtn");
    const cancelBtn = document.getElementById("cameraCancelBtn");
    const flipBtn = document.getElementById("cameraFlipBtn");

    async function openCameraForInput(inputId) {
        currentTargetInputId = inputId;
        modal.style.display = "flex";

        stopStream();

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: facingMode } },
                audio: false
            });

            video.srcObject = stream;
            await video.play();
        } catch (err) {
            alert("Camera access failed: " + err.message);
            closeModal();
        }
    }

    function stopStream() {
        if (stream) stream.getTracks().forEach(t => t.stop());
    }

    function closeModal() {
        stopStream();
        modal.style.display = "none";
        currentTargetInputId = null;
    }

    async function capturePhoto() {
        if (!video || !canvas) return;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const ctx = canvas.getContext("2d");
        if (facingMode === 'user') {
            // Mirror the image if using front camera
            ctx.translate(canvas.width, 0);
            ctx.scale(-1, 1);
        }
        ctx.drawImage(video, 0, 0);

        const blob = await new Promise(resolve =>
            canvas.toBlob(resolve, "image/jpeg", 0.9)
        );

        const file = new File([blob], `capture_${Date.now()}.jpg`, {
            type: "image/jpeg"
        });

        if (currentTargetInputId) {
            const input = document.getElementById(currentTargetInputId);
            if (input) {
                const dt = new DataTransfer();

                // If input is multiple, preserve existing files and append new one
                if (input.multiple && input.files) {
                    Array.from(input.files).forEach(f => dt.items.add(f));
                }

                dt.items.add(file);
                input.files = dt.files;

                // Trigger change event so previews update
                const event = new Event('change', { bubbles: true });
                input.dispatchEvent(event);
            }
        }

        closeModal();
    }

    function bindCameraButtons() {
        document.querySelectorAll(".open-camera").forEach(btn => {
            // If already bound, skip or remove old listener? 
            // The provided code checks dataset.bound.
            if (btn.dataset.bound) return;
            btn.dataset.bound = "1";

            btn.addEventListener("click", (e) => {
                e.preventDefault(); // Prevent default button behavior
                const inputId = btn.dataset.target;
                if (inputId) {
                    openCameraForInput(inputId);
                } else {
                    console.error("No data-target found on camera button");
                }
            });
        });
    }

    // Bind initial buttons
    bindCameraButtons();

    // Also observe for new buttons (DOM mutations) since we have dynamic rows in Step 2/4
    const observer = new MutationObserver((mutations) => {
        bindCameraButtons();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    if (flipBtn) {
        flipBtn.addEventListener("click", () => {
            facingMode = facingMode === "user" ? "environment" : "user";
            // restart stream
            if (currentTargetInputId) openCameraForInput(currentTargetInputId);
        });
    }

    if (captureBtn) captureBtn.addEventListener("click", capturePhoto);
    if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

})();
