(function () {
  var installButton = document.getElementById("pwaInstallBtn");
  var hintNode = document.getElementById("pwaInstallHint");
  if (!installButton) return;

  var deferredPrompt = null;
  var ua = (navigator.userAgent || "").toLowerCase();
  var isIOS = /iphone|ipad|ipod/.test(ua);
  var isIOSChromeFamily = /crios|fxios|edgios|opios/.test(ua);
  var isIOSSafari = isIOS && /safari/.test(ua) && !isIOSChromeFamily;
  var isAndroidChrome = /android/.test(ua) && /chrome/.test(ua) && !/edg|opr/.test(ua);
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

  function showHintTemporary(text, timeoutMs) {
    if (!hintNode) return;
    showHint(text);
    var delay = Number(timeoutMs) > 0 ? Number(timeoutMs) : 5000;
    window.setTimeout(function () {
      hintNode.hidden = true;
    }, delay);
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
      showHintTemporary("iPhone/iPad: tap Share and choose Add to Home Screen.");
      return;
    }

    if (!hasSecureContext) {
      if (isAndroidChrome) {
        showHintTemporary("Chrome blocks install on http://IP links. Use HTTPS or native APK.");
      } else {
        showHintTemporary("Use HTTPS to enable browser install.");
      }
      return;
    }

    showHintTemporary("Install option not available in this browser. Use Chrome on Android.");
  });

  if (isIOSSafari) {
    showInstallButton("Add to Home Screen");
    showHint("iPhone/iPad: tap Share and choose Add to Home Screen.");
    return;
  }

  if (!hasSecureContext) {
    showInstallButton("Install App");
  }
})();
