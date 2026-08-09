/* AiCIV structured Needs You decisions — durable human judgment, not side-effect execution. */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const REGISTRY = window.__HERMES_PLUGINS__;
  if (!SDK || !REGISTRY) return;

  const React = SDK.React;
  const h = React.createElement;
  const useEffect = SDK.hooks.useEffect;
  const useMemo = SDK.hooks.useMemo;
  const useState = SDK.hooks.useState;
  const BASE = window.__HERMES_BASE_PATH__ || "";
  const API = "/api/plugins/aiciv-workspace/decisions";

  function isAiCivRootRoute() {
    const base = String(BASE || "").replace(/\/+$/, "");
    let path = window.location.pathname || "/";
    if (base && path.startsWith(base)) path = path.slice(base.length) || "/";
    return path === "/";
  }

  function currentView() {
    if (!isAiCivRootRoute()) return null;
    return new URLSearchParams(window.location.search).get("aiciv") || "now";
  }

  function requestId() {
    const value = window.crypto && typeof window.crypto.randomUUID === "function"
      ? window.crypto.randomUUID()
      : String(Date.now()) + "-" + Math.random().toString(16).slice(2);
    return "web:" + value;
  }

  function displayTime(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
  }

  function usePendingDecisions() {
    const [state, setState] = useState({ loading: true, decisions: [], error: null });

    useEffect(function () {
      let disposed = false;
      let timer = null;

      async function refresh() {
        try {
          const body = await SDK.fetchJSON(API + "?status=pending&limit=100");
          if (!disposed) {
            setState({
              loading: false,
              decisions: body && Array.isArray(body.decisions) ? body.decisions : [],
              error: null
            });
          }
        } catch (error) {
          if (!disposed) setState(function (previous) {
            return Object.assign({}, previous, { loading: false, error: error });
          });
        }
      }

      refresh();
      timer = window.setInterval(refresh, 10000);
      return function () {
        disposed = true;
        if (timer) window.clearInterval(timer);
      };
    }, []);

    return [state, function () {
      return SDK.fetchJSON(API + "?status=pending&limit=100").then(function (body) {
        const decisions = body && Array.isArray(body.decisions) ? body.decisions : [];
        setState({ loading: false, decisions: decisions, error: null });
        return decisions;
      });
    }];
  }

  function RefList(props) {
    const refs = Array.isArray(props.refs) ? props.refs : [];
    if (!refs.length) return null;
    return h("div", { className: "aiciv-receipts" },
      h("span", { className: "aiciv-receipts__label" }, props.label),
      refs.map(function (ref) {
        return h("span", { key: ref }, ref);
      })
    );
  }

  function DecisionCard(props) {
    const decision = props.decision;
    const [note, setNote] = useState("");
    const [submitting, setSubmitting] = useState("");
    const [error, setError] = useState("");

    async function respond(optionId) {
      if (submitting) return;
      setSubmitting(optionId);
      setError("");
      try {
        const body = await SDK.fetchJSON(API + "/" + encodeURIComponent(decision.decisionId) + "/respond", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ optionId: optionId, note: note, requestId: requestId() })
        });
        const receipt = body && body.receipt;
        props.onRecorded({
          title: decision.title,
          optionId: optionId,
          receiptId: receipt && receipt.receiptId,
          recordedAt: receipt && receipt.recordedAt
        });
        await props.refresh();
      } catch (err) {
        setError(err && err.message ? err.message : "Decision response could not be recorded.");
      } finally {
        setSubmitting("");
      }
    }

    const options = Array.isArray(decision.options) ? decision.options : [];
    return h("article", { className: "aiciv-item", "data-decision-id": decision.decisionId },
      h("div", { className: "aiciv-item__meta" },
        h("span", null, decision.urgency === "high" ? "High priority" : "Needs you"),
        decision.createdBy ? h("span", null, "Asked by " + decision.createdBy) : null,
        displayTime(decision.createdAt) ? h("span", null, displayTime(decision.createdAt)) : null,
        h("span", null, "decision:" + decision.decisionId)
      ),
      h("h3", { className: "aiciv-item__title" }, decision.title),
      h("p", { className: "aiciv-item__body" }, decision.question),
      decision.rationale
        ? h("p", { className: "aiciv-item__body" }, "Why this needs judgment: " + decision.rationale)
        : null,
      decision.recommendation
        ? h("p", { className: "aiciv-item__body" }, "AiCIV recommendation: " + decision.recommendation)
        : null,
      h(RefList, { label: "Evidence", refs: decision.evidenceRefs }),
      h(RefList, { label: "Blocking work", refs: decision.blockingRefs }),
      h("label", { className: "aiciv-decision-note" },
        h("span", null, "Optional note"),
        h("textarea", {
          value: note,
          maxLength: 8000,
          onChange: function (event) { setNote(event.target.value); },
          placeholder: "Context for the AiCIV"
        })
      ),
      h("div", { className: "aiciv-item__actions" },
        options.map(function (option) {
          const recommended = option.id === decision.recommendation;
          return h("button", {
            key: option.id,
            type: "button",
            className: "aiciv-text-button",
            disabled: Boolean(submitting),
            onClick: function () { respond(option.id); },
            title: option.description || option.label
          }, (submitting === option.id ? "Recording… " : "") + option.label + (recommended ? " · recommended" : ""));
        })
      ),
      error ? h("p", { className: "aiciv-error", role: "status" }, error) : null,
      h("p", { className: "aiciv-decision-semantics" },
        "Your choice records human judgment. Any downstream action still requires its own execution receipt."
      )
    );
  }

  function DecisionsProjection() {
    const view = currentView();
    const [state, refresh] = usePendingDecisions();
    const [lastReceipt, setLastReceipt] = useState(null);

    const decisions = useMemo(function () {
      return state.decisions.slice().sort(function (a, b) {
        if (a.urgency === b.urgency) return String(b.createdAt || "").localeCompare(String(a.createdAt || ""));
        return a.urgency === "high" ? -1 : 1;
      });
    }, [state.decisions]);

    if (view !== "now" && view !== "needs") return null;

    if (view === "now") {
      if (!state.loading && !state.error && decisions.length === 0) return null;
      return h("section", { className: "aiciv-section", "data-aiciv-authority": "aiciv-decisions" },
        h("div", { className: "aiciv-section__head" },
          h("h2", null, "Needs Your Decision"),
          h("a", { href: BASE + "/?aiciv=needs" }, "Open Needs You →")
        ),
        state.error
          ? h("p", { className: "aiciv-error" }, "Decision state is unavailable. AiCIV will not invent pending approvals.")
          : state.loading
            ? h("p", { className: "aiciv-empty" }, "Reading pending decisions.")
            : h("div", { className: "aiciv-item__meta" },
                h("span", null, decisions.length + " pending"),
                h("span", null, decisions.filter(function (item) { return item.urgency === "high"; }).length + " high priority")
              )
      );
    }

    return h("section", { className: "aiciv-section", "data-aiciv-authority": "aiciv-decisions" },
      h("div", { className: "aiciv-section__head" },
        h("h2", null, "Structured Decisions"),
        h("span", null, decisions.length + " pending")
      ),
      lastReceipt
        ? h("article", { className: "aiciv-decision-confirmation", role: "status" },
            h("strong", null, "Decision recorded"),
            h("span", null, lastReceipt.title + " · " + lastReceipt.optionId),
            lastReceipt.receiptId ? h("span", null, "receipt:" + lastReceipt.receiptId) : null,
            h("span", null, "No downstream action is implied by this receipt.")
          )
        : null,
      state.error
        ? h("p", { className: "aiciv-error" }, "Decision state is unavailable. AiCIV will not invent pending approvals.")
        : state.loading
          ? h("p", { className: "aiciv-empty" }, "Reading pending decisions.")
          : decisions.length
            ? h("div", { className: "aiciv-list" }, decisions.map(function (decision) {
                return h(DecisionCard, {
                  key: decision.decisionId,
                  decision: decision,
                  refresh: refresh,
                  onRecorded: setLastReceipt
                });
              }))
            : h("p", { className: "aiciv-empty" }, "Nothing currently requires structured human judgment.")
    );
  }

  REGISTRY.registerSlot("aiciv-structured-decisions", "post-main", DecisionsProjection);
})();
