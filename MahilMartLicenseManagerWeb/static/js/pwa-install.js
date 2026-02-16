(function () {
  var installButton = document.getElementById("pwaInstallBtn");
  var hintNode = document.getElementById("pwaInstallHint");
  if (!installButton) return;

  var deferredPrompt = null;
  var ua = (navigator.userAgent || "").toLowerCase();
  var isIOS = /iphone|ipad|ipod/.test(ua);
  var isIOSChromeFamily = /crios|fxios|edgios|opios/.test(ua);
  var isIOSSafari = isIOS && /safari/.test(ua) && !isIOSChromeFamily;
  var isIOSOtherBrowser = isIOS && !isIOSSafari;
  var isAndroid = /android/.test(ua);
  var isMobile = isAndroid || isIOS;
  var isDesktopChromium = !isMobile && /(?:chrome|edg)\//.test(ua);
  var isAndroidChrome = /android/.test(ua) && /chrome/.test(ua) && !/edg|opr/.test(ua);
  var isStandalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  var hostname = (location.hostname || "").toLowerCase();
  var isLoopbackHost =
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "::1" ||
    hostname.endsWith(".localhost");
  var isPrivateIpv4 =
    /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(hostname);
  var hasSecureContext = window.isSecureContext === true || isLoopbackHost;

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
      try {
        deferredPrompt.prompt();
      } catch (err) {
        deferredPrompt = null;
        showHintTemporary("Install prompt blocked. Use browser menu (...) > Install app.");
        return;
      }

      Promise.resolve(deferredPrompt.userChoice).catch(function () {
        return null;
      }).finally(function () {
        deferredPrompt = null;
      });
      return;
    }

    if (isIOSSafari) {
      showHintTemporary("iOS shortcut: tap Share and choose Add to Home Screen.");
      return;
    }

    if (isIOSOtherBrowser) {
      showHintTemporary("On iPhone/iPad, open this site in Safari and use Share > Add to Home Screen.");
      return;
    }

    if (!hasSecureContext) {
      if (isAndroidChrome) {
        showHintTemporary("Chrome blocks install on http://IP links. Use HTTPS or native APK.");
      } else if (!isMobile && isPrivateIpv4) {
        showHintTemporary("Install App on IP needs HTTPS. Use HTTPS URL or installer app.");
      } else {
        showHintTemporary("Use HTTPS to enable browser install.");
      }
      return;
    }

    if (isDesktopChromium) {
      showHintTemporary("If prompt is not shown, use browser menu (...) > Install app.");
      return;
    }

    if (isAndroid) {
      showHintTemporary("Install prompt not ready yet. Refresh and try again.");
      return;
    }

    showHintTemporary("Install is not supported in this browser.");
  });

  if (isIOS) {
    showInstallButton("Install Shortcut");
    return;
  }

  if (!hasSecureContext) {
    if (isAndroidChrome && isPrivateIpv4) {
      showHint(
        "Install App needs HTTPS. On Android, http://IP links cannot trigger install prompt."
      );
    } else if (!isMobile && isPrivateIpv4) {
      showHint("Install App on IP needs HTTPS. Use HTTPS URL or installer app.");
    } else {
      showHint("Install App requires HTTPS or localhost.");
    }
    installButton.hidden = true;
    return;
  }

  showInstallButton("Install App");
})();
