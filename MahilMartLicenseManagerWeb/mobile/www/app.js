(function () {
  var statusNode = document.getElementById("status");
  var manualUrlInput = document.getElementById("manualUrl");
  var connectBtn = document.getElementById("connectBtn");
  var rescanBtn = document.getElementById("rescanBtn");

  var config = {
    fixedUrl: "",
    port: 8001,
    healthPath: "/healthz/",
  };

  var commonSubnets = [
    "192.168.1",
    "192.168.0",
    "10.0.0",
    "10.0.1",
    "172.16.0",
    "172.16.1",
  ];

  function setStatus(text) {
    if (statusNode) statusNode.textContent = text;
  }

  function normalizeUrl(value) {
    var raw = (value || "").trim();
    if (!raw) return "";
    try {
      var parsed = new URL(raw);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return "";
      parsed.hash = "";
      parsed.search = "";
      return parsed.toString().replace(/\/$/, "");
    } catch (_err) {
      return "";
    }
  }

  function withTimeout(ms, promiseFactory) {
    var controller = new AbortController();
    var timer = setTimeout(function () {
      controller.abort();
    }, ms);

    return promiseFactory(controller.signal).finally(function () {
      clearTimeout(timer);
    });
  }

  async function probeServer(baseUrl) {
    var normalized = normalizeUrl(baseUrl);
    if (!normalized) return false;

    var healthUrl = normalized + (config.healthPath || "/healthz/");
    try {
      var response = await withTimeout(900, function (signal) {
        return fetch(healthUrl, {
          method: "GET",
          cache: "no-store",
          mode: "cors",
          signal: signal,
        });
      });

      if (!response.ok) return false;
      var payload = await response.json().catch(function () {
        return null;
      });
      return Boolean(payload && payload.status === "ok");
    } catch (_err) {
      return false;
    }
  }

  function saveServerUrl(url) {
    var normalized = normalizeUrl(url);
    if (!normalized) return;
    localStorage.setItem("mmlm_server_url", normalized);

    try {
      var hostname = new URL(normalized).hostname;
      var parts = hostname.split(".");
      if (parts.length === 4) {
        localStorage.setItem("mmlm_last_subnet", parts.slice(0, 3).join("."));
      }
    } catch (_err) {
      // ignore parse issues
    }
  }

  function openServer(url) {
    var normalized = normalizeUrl(url);
    if (!normalized) return;
    saveServerUrl(normalized);
    setStatus("Connected. Opening app...");
    window.location.href = normalized + "/";
  }

  async function getDeviceSubnetFromWebRTC() {
    return new Promise(function (resolve) {
      var RTCPeerConnectionCtor = window.RTCPeerConnection || window.webkitRTCPeerConnection;
      if (!RTCPeerConnectionCtor) {
        resolve("");
        return;
      }

      var done = false;
      function finish(value) {
        if (done) return;
        done = true;
        resolve(value || "");
      }

      var pc = new RTCPeerConnectionCtor({ iceServers: [] });
      pc.createDataChannel("scan");

      pc.onicecandidate = function (event) {
        if (!event || !event.candidate || !event.candidate.candidate) return;
        var candidate = event.candidate.candidate;
        var match = candidate.match(/(\d{1,3}\.){3}\d{1,3}/);
        if (!match) return;
        var ip = match[0];
        if (ip.startsWith("127.")) return;
        var parts = ip.split(".");
        if (parts.length === 4) {
          finish(parts.slice(0, 3).join("."));
        }
      };

      pc.createOffer()
        .then(function (offer) {
          return pc.setLocalDescription(offer);
        })
        .catch(function () {
          finish("");
        });

      setTimeout(function () {
        finish("");
      }, 1200);
    });
  }

  async function scanSubnet(subnet) {
    if (!subnet) return "";
    setStatus("Scanning subnet " + subnet + ".x ...");

    var found = "";
    var currentHost = 2;
    var maxHost = 254;
    var workers = 24;

    async function worker() {
      while (!found && currentHost <= maxHost) {
        var host = currentHost;
        currentHost += 1;
        var candidateUrl = "http://" + subnet + "." + host + ":" + config.port;
        var ok = await probeServer(candidateUrl);
        if (ok) {
          found = candidateUrl;
          break;
        }
      }
    }

    var jobs = [];
    for (var i = 0; i < workers; i += 1) {
      jobs.push(worker());
    }
    await Promise.all(jobs);
    return found;
  }

  async function detectAndConnect() {
    connectBtn.disabled = true;
    rescanBtn.disabled = true;

    var fixed = normalizeUrl(config.fixedUrl || "");
    if (fixed) {
      setStatus("Trying fixed URL: " + fixed);
      if (await probeServer(fixed)) {
        openServer(fixed);
        return;
      }
    }

    var saved = normalizeUrl(localStorage.getItem("mmlm_server_url") || "");
    if (saved) {
      setStatus("Trying last known URL: " + saved);
      if (await probeServer(saved)) {
        openServer(saved);
        return;
      }
    }

    var subnetCandidates = [];
    var rememberedSubnet = (localStorage.getItem("mmlm_last_subnet") || "").trim();
    if (rememberedSubnet) subnetCandidates.push(rememberedSubnet);

    var rtcSubnet = await getDeviceSubnetFromWebRTC();
    if (rtcSubnet && subnetCandidates.indexOf(rtcSubnet) === -1) {
      subnetCandidates.push(rtcSubnet);
    }

    commonSubnets.forEach(function (subnet) {
      if (subnetCandidates.indexOf(subnet) === -1) {
        subnetCandidates.push(subnet);
      }
    });

    for (var i = 0; i < subnetCandidates.length; i += 1) {
      var subnet = subnetCandidates[i];
      var discovered = await scanSubnet(subnet);
      if (discovered) {
        openServer(discovered);
        return;
      }
    }

    setStatus("Auto detect failed. Enter server URL manually and tap Connect.");
    connectBtn.disabled = false;
    rescanBtn.disabled = false;
  }

  async function connectManual() {
    var value = normalizeUrl(manualUrlInput.value);
    if (!value) {
      setStatus("Enter valid URL. Example: http://192.168.1.20:8001");
      return;
    }

    setStatus("Checking manual URL...");
    connectBtn.disabled = true;
    rescanBtn.disabled = true;

    var ok = await probeServer(value);
    if (!ok) {
      setStatus("Server not reachable at " + value + ". Check Wi-Fi and server app.");
      connectBtn.disabled = false;
      rescanBtn.disabled = false;
      return;
    }

    openServer(value);
  }

  function loadConfig() {
    return fetch("./server-config.json", { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (json) {
        if (json && typeof json === "object") {
          config.fixedUrl = normalizeUrl(json.fixedUrl || "");
          config.port = Number(json.port) || 8001;
          config.healthPath = typeof json.healthPath === "string" ? json.healthPath : "/healthz/";
        }
      })
      .catch(function () {
        // keep defaults
      });
  }

  connectBtn.addEventListener("click", function () {
    connectManual();
  });

  rescanBtn.addEventListener("click", function () {
    detectAndConnect();
  });

  loadConfig().finally(function () {
    var saved = normalizeUrl(localStorage.getItem("mmlm_server_url") || "");
    if (saved) {
      manualUrlInput.value = saved;
    } else if (config.fixedUrl) {
      manualUrlInput.value = config.fixedUrl;
    }
    detectAndConnect();
  });
})();
