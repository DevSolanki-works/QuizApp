(function () {
  "use strict";

  var ADSENSE_CLIENT = "ca-pub-4922314688440658";
  var PROD_BACKEND_HTTP = "https://forge-backend-878124462453.us-central1.run.app";

  function readTargetOverride() {
    try {
      return new URLSearchParams(window.location.search).get("target");
    } catch (_) {
      return null;
    }
  }

  var protocol = window.location.protocol;
  var hostname = window.location.hostname;
  var bridgeSaysNative = false;

  try {
    bridgeSaysNative =
      typeof window.Capacitor !== "undefined" &&
      typeof window.Capacitor.isNativePlatform === "function" &&
      window.Capacitor.isNativePlatform();
  } catch (_) {
    bridgeSaysNative = false;
  }

  var isNativeApp =
    protocol === "capacitor:" ||
    (protocol === "https:" && hostname === "localhost") ||
    bridgeSaysNative;

  var isLocalDev =
    !isNativeApp &&
    (protocol === "file:" ||
      ((protocol === "http:" || protocol === "https:") &&
        (hostname === "localhost" || hostname === "127.0.0.1")));

  var override = readTargetOverride();
  var target = isNativeApp || override === "app" ? "app" : "web";
  var isWebsite = target === "web";

  var config = {
    target: target,
    isWebsite: isWebsite,
    isNativeApp: isNativeApp,
    isLocalDev: isLocalDev,
    appOnlyFeaturesEnabled: target === "app",
    monetization: target === "app" ? "admob" : "adsense",
    adsenseClient: ADSENSE_CLIENT,
    adsenseEnabled: isWebsite && !isLocalDev,
    backendHttp: isLocalDev ? "http://127.0.0.1:8000" : PROD_BACKEND_HTTP,
  };

  function installVisibilityStyles() {
    if (document.getElementById("forge-platform-visibility")) return;
    var style = document.createElement("style");
    style.id = "forge-platform-visibility";
    style.textContent = [
      'html[data-forge-target="web"] [data-app-only]{display:none!important;}',
      'html[data-forge-target="app"] [data-web-only]{display:none!important;}',
      'html[data-forge-target="app"] .adsbygoogle{display:none!important;}',
    ].join("");
    document.head.appendChild(style);
  }

  function loadAdSense() {
    if (!config.adsenseEnabled) return false;
    if (document.querySelector("script[data-forge-adsense]")) return true;

    var script = document.createElement("script");
    script.async = true;
    script.src =
      "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=" +
      ADSENSE_CLIENT;
    script.crossOrigin = "anonymous";
    script.dataset.forgeAdsense = "true";
    document.head.appendChild(script);
    return true;
  }

  document.documentElement.dataset.forgeTarget = target;
  document.documentElement.dataset.forgeMonetization = config.monetization;
  installVisibilityStyles();

  window.FORGE_PLATFORM = config;
  window.ForgePlatform = {
    config: config,
    loadAdSense: loadAdSense,
  };
})();
