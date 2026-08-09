/* AiCIV dashboard entrypoint. Loads the stable workspace UI first, then optional media runtime. */
(function () {
  "use strict";

  const current = document.currentScript;
  if (!current || !current.src) {
    console.error("[AiCIV] Cannot resolve dashboard plugin base URL.");
    return;
  }

  const base = new URL(".", current.src);

  function load(name) {
    return new Promise(function (resolve, reject) {
      const script = document.createElement("script");
      script.src = new URL(name, base).toString();
      script.async = false;
      script.dataset.aicivModule = name;
      script.onload = function () { resolve(); };
      script.onerror = function () { reject(new Error("AiCIV module failed to load: " + name)); };
      document.head.appendChild(script);
    });
  }

  load("index.js")
    .then(function () { return load("talk-live.js"); })
    .catch(function (error) {
      console.error("[AiCIV] Dashboard module load failure", error);
      window.dispatchEvent(new CustomEvent("aiciv:presence:state", {
        detail: { state: "error", active: false, muted: false, message: "AiCIV voice module could not be loaded." }
      }));
    });
})();
