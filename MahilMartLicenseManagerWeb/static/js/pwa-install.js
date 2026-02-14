(function () {
  var installButton = document.getElementById("pwaInstallBtn");
  var hintNode = document.getElementById("pwaInstallHint");
  if (!installButton) return;

  var deferredPrompt = null;
  var ua = (navigator.userAgent || "").toLowerCase();
  var isIOS = /iphone|ipad|ipod/.test(ua);
  var isIOSChromeFamily = /crios|fxios|edgios|opios/.test(ua);
  var isIOSSafari = isIOS && /safari/.test(ua) && !isIOSChromeFamily;
  var isStandalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  var isLocalhost = location.hostname === "127.0.0.1" || location.hostname === "localhost";
  var hasSecureContext = location.protocol === "https:" || isLocalhost;

  function showInstallButton(labelText) {
    var label = installButton.querySelector("span");
    if (label && labelText) {
      label.textContent = labelText;
    }
    installButton.hidden = false;
  }

  function showHint(text) {
    if (!hintNode) return;
    hintNode.textContent = text;
    hintNode.hidden = false;
  }

  function hideInstallControls() {
    installButton.hidden = true;
    if (hintNode) hintNode.hidden = true;
  }

  if (isStandalone) {
    hideInstallControls();
    return;
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredPrompt = event;
    showInstallButton("Install App");
    if (!hasSecureContext) {
      showHint("Use HTTPS for reliable install support.");
    }
  });

  window.addEventListener("appinstalled", function () {
    deferredPrompt = null;
    hideInstallControls();
  });

  installButton.addEventListener("click", function () {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () {
        deferredPrompt = null;
      });
      return;
    }

    if (isIOSSafari) {
      showHint("iPhone/iPad: tap Share and choose Add to Home Screen.");
      return;
    }

    if (!hasSecureContext) {
      showHint("Install prompt may be blocked on non-HTTPS pages.");
      return;
    }

    showHint("Install option not available in this browser. Use Chrome on Android.");
  });

  if (isIOSSafari) {
    showInstallButton("Add to Home Screen");
    showHint("iPhone/iPad: tap Share and choose Add to Home Screen.");
    return;
  }

  if (!hasSecureContext) {
    showInstallButton("Install App");
    showHint("Switch to HTTPS for best install support.");
  }
})();
