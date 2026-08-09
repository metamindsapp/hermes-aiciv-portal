/* AiCIV Talk Live runtime — real ElevenLabs WebRTC, no long-lived browser credential. */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const REGISTRY = window.__HERMES_PLUGINS__;
  if (!SDK || !REGISTRY) return;

  const React = SDK.React;
  const h = React.createElement;
  const useState = SDK.hooks.useState;
  const useEffect = SDK.hooks.useEffect;

  // Exact browser SDK version. Loaded only after the human explicitly starts voice.
  const ELEVENLABS_CLIENT_SRC = "https://unpkg.com/@elevenlabs/client@1.11.1/dist/lib.iife.js";
  const ELEVENLABS_CLIENT_VERSION = "1.11.1";
  let sdkPromise = null;
  let conversation = null;
  let startPromise = null;
  let state = "idle";
  let muted = false;
  let conversationId = "";

  function emit(next, extra) {
    state = next;
    const detail = Object.assign({
      state: state,
      active: Boolean(conversation) || state === "connecting" || state === "disconnecting",
      muted: muted,
      conversationId: conversationId || null,
      provider: "elevenlabs",
      transport: "webrtc"
    }, extra || {});
    window.dispatchEvent(new CustomEvent("aiciv:presence:state", { detail: detail }));
  }

  function errorMessage(error) {
    if (!error) return "Voice connection failed.";
    if (typeof error === "string") return error.slice(0, 240);
    if (typeof error.message === "string") return error.message.slice(0, 240);
    return "Voice connection failed.";
  }

  function loadClient() {
    if (window.ElevenLabsClient && window.ElevenLabsClient.Conversation) {
      return Promise.resolve(window.ElevenLabsClient);
    }
    if (sdkPromise) return sdkPromise;

    sdkPromise = new Promise(function (resolve, reject) {
      const selector = 'script[data-aiciv-elevenlabs-client="' + ELEVENLABS_CLIENT_VERSION + '"]';
      const existing = document.querySelector(selector);

      function validate() {
        if (window.ElevenLabsClient && window.ElevenLabsClient.Conversation) {
          resolve(window.ElevenLabsClient);
        } else {
          reject(new Error("ElevenLabs browser client loaded without Conversation support."));
        }
      }

      if (existing) {
        if (window.ElevenLabsClient && window.ElevenLabsClient.Conversation) {
          validate();
          return;
        }
        existing.addEventListener("load", validate, { once: true });
        existing.addEventListener("error", function () {
          reject(new Error("ElevenLabs browser client could not be loaded."));
        }, { once: true });
        return;
      }

      const script = document.createElement("script");
      script.src = ELEVENLABS_CLIENT_SRC;
      script.async = true;
      script.crossOrigin = "anonymous";
      script.dataset.aicivElevenlabsClient = ELEVENLABS_CLIENT_VERSION;
      script.onload = validate;
      script.onerror = function () {
        reject(new Error("ElevenLabs browser client could not be loaded."));
      };
      document.head.appendChild(script);
    }).catch(function (error) {
      sdkPromise = null;
      throw error;
    });

    return sdkPromise;
  }

  async function requestMicrophonePermission() {
    if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
      throw new Error("This browser does not expose microphone access.");
    }
    const permissionStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    permissionStream.getTracks().forEach(function (track) { track.stop(); });
  }

  async function mintConversationToken(endpoint) {
    const response = await SDK.fetchJSON(endpoint, { method: "POST" });
    if (!response || typeof response.token !== "string" || !response.token) {
      throw new Error("Presence did not return a conversation token.");
    }
    return {
      token: response.token,
      conversationId: typeof response.conversationId === "string" ? response.conversationId : ""
    };
  }

  async function start(endpoint) {
    if (conversation) return conversation;
    if (startPromise) return startPromise;

    startPromise = (async function () {
      muted = false;
      conversationId = "";
      emit("connecting");

      try {
        // Permission is requested only from a human gesture. The test stream is
        // immediately closed; the ElevenLabs SDK creates the actual media track.
        await requestMicrophonePermission();
        const client = await loadClient();
        const credential = await mintConversationToken(endpoint);
        conversationId = credential.conversationId;

        const session = await client.Conversation.startSession({
          conversationToken: credential.token,
          connectionType: "webrtc",
          onConnect: function () {
            if (!muted) emit("listening");
          },
          onDisconnect: function () {
            conversation = null;
            muted = false;
            emit("idle");
          },
          onError: function (error) {
            emit("error", { message: errorMessage(error) });
          },
          onStatusChange: function (value) {
            const status = typeof value === "string" ? value : value && value.status;
            if (status === "connecting") emit("connecting");
            if (status === "connected" && !muted && state !== "speaking") emit("listening");
            if (status === "disconnecting") emit("disconnecting");
            if (status === "disconnected") {
              conversation = null;
              muted = false;
              emit("idle");
            }
          },
          onModeChange: function (value) {
            const mode = typeof value === "string" ? value : value && value.mode;
            if (!muted && (mode === "speaking" || mode === "listening")) emit(mode);
          }
        });

        conversation = session;
        if (session && typeof session.getId === "function") {
          conversationId = session.getId() || conversationId;
        }
        if (state === "connecting") emit("listening");
        return session;
      } catch (error) {
        conversation = null;
        muted = false;
        emit("error", { message: errorMessage(error) });
        throw error;
      } finally {
        startPromise = null;
      }
    })();

    return startPromise;
  }

  async function stop() {
    const current = conversation;
    conversation = null;
    muted = false;
    if (!current) {
      emit("idle");
      return;
    }

    emit("disconnecting");
    try {
      await current.endSession();
    } catch (error) {
      emit("error", { message: errorMessage(error) });
      throw error;
    } finally {
      conversation = null;
      muted = false;
      emit("idle");
    }
  }

  function toggleMute() {
    if (!conversation || typeof conversation.setMicMuted !== "function") return;
    const next = !muted;
    try {
      conversation.setMicMuted(next);
      muted = next;
      emit(muted ? "muted" : "listening");
    } catch (error) {
      emit("error", { message: errorMessage(error) });
    }
  }

  window.addEventListener("aiciv:presence:start", function (event) {
    const endpoint = event && event.detail && event.detail.tokenEndpoint;
    if (typeof endpoint !== "string" || !endpoint.startsWith("/api/plugins/aiciv-workspace/")) {
      emit("error", { message: "Voice token endpoint was invalid." });
      return;
    }
    const active = Boolean(conversation) || state === "connecting" || state === "disconnecting";
    if (active) {
      stop().catch(function () {});
    } else {
      start(endpoint).catch(function () {});
    }
  });

  window.addEventListener("aiciv:presence:mute", function () {
    toggleMute();
  });

  // Exposed for diagnostics/tests; contains controls and state, never the token.
  window.__AICIV_PRESENCE_VOICE__ = {
    start: start,
    stop: stop,
    toggleMute: toggleMute,
    snapshot: function () {
      return {
        state: state,
        active: Boolean(conversation) || state === "connecting" || state === "disconnecting",
        muted: muted,
        conversationId: conversationId || null,
        provider: "elevenlabs",
        transport: "webrtc"
      };
    }
  };

  function MuteControl() {
    const [voiceState, setVoiceState] = useState(state);
    const [isMuted, setIsMuted] = useState(muted);

    useEffect(function () {
      function onState(event) {
        const detail = event && event.detail ? event.detail : {};
        if (typeof detail.state === "string") setVoiceState(detail.state);
        if (typeof detail.muted === "boolean") setIsMuted(detail.muted);
      }
      window.addEventListener("aiciv:presence:state", onState);
      return function () { window.removeEventListener("aiciv:presence:state", onState); };
    }, []);

    const active = voiceState === "listening" || voiceState === "speaking" || voiceState === "muted";
    if (!active) return null;

    return h("button", {
      type: "button",
      className: "aiciv-presence-mute",
      onClick: function () { window.dispatchEvent(new CustomEvent("aiciv:presence:mute")); },
      "aria-pressed": isMuted,
      title: isMuted ? "Unmute microphone" : "Mute microphone"
    }, isMuted ? "Unmute" : "Mute");
  }

  // Separate slot identity preserves the workspace's existing Talk Live control.
  REGISTRY.registerSlot("aiciv-talk-live", "header-right", MuteControl);
})();
