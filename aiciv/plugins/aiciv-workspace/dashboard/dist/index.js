/* AiCIV workspace dashboard plugin — no bundled React. */
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const REGISTRY = window.__HERMES_PLUGINS__;
  if (!SDK || !REGISTRY) return;

  const React = SDK.React;
  const h = React.createElement;
  const useState = SDK.hooks.useState;
  const useEffect = SDK.hooks.useEffect;
  const useMemo = SDK.hooks.useMemo;
  const BASE = window.__HERMES_BASE_PATH__ || "";
  const API = "/api/plugins/aiciv-workspace";
  const ACTIVE = new Set(["queued", "accepted", "running", "waiting", "cancel_requested"]);
  const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);

  function fullDate(date) {
    const weekday = new Intl.DateTimeFormat("en", { weekday: "long" }).format(date);
    const month = new Intl.DateTimeFormat("en", { month: "long" }).format(date);
    return weekday + ", " + date.getDate() + " " + month + " " + date.getFullYear();
  }

  function fmtTime(value) {
    if (!value) return "";
    const date = typeof value === "number"
      ? new Date(value < 100000000000 ? value * 1000 : value)
      : new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString();
  }

  function resultText(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "object") {
      const keys = ["summary", "answer", "result", "conclusion", "message"];
      for (const key of keys) {
        if (typeof value[key] === "string") return value[key];
      }
    }
    try { return JSON.stringify(value, null, 2); } catch (_) { return String(value); }
  }

  function objectHref(view) {
    return BASE + "/?aiciv=" + encodeURIComponent(view);
  }

  function hermesHref(path) {
    return BASE + path;
  }

  function usePoll(loader, intervalMs) {
    const [state, setState] = useState({ loading: true, value: null, error: null });
    useEffect(function () {
      let disposed = false;
      let timer = null;
      function run() {
        Promise.resolve()
          .then(loader)
          .then(function (value) {
            if (!disposed) setState({ loading: false, value: value, error: null });
          })
          .catch(function (error) {
            if (!disposed) setState(function (previous) {
              return { loading: false, value: previous.value, error: error };
            });
          })
          .finally(function () {
            if (!disposed && intervalMs) timer = window.setTimeout(run, intervalMs);
          });
      }
      run();
      return function () {
        disposed = true;
        if (timer) window.clearTimeout(timer);
      };
    }, []);
    return state;
  }

  function loadWorkspace() {
    return Promise.allSettled([
      SDK.api.getStatus(),
      SDK.api.getSessions(20, 0, "", "recent"),
      SDK.fetchJSON(API + "/jobs?limit=100"),
      SDK.fetchJSON(API + "/projects"),
      SDK.fetchJSON(API + "/activity?limit=100"),
      SDK.fetchJSON(API + "/references"),
      SDK.fetchJSON(API + "/presence/ready")
    ]).then(function (results) {
      function value(index, fallback) {
        return results[index].status === "fulfilled" ? results[index].value : fallback;
      }
      return {
        status: value(0, null),
        sessions: value(1, { sessions: [], total: 0 }),
        jobs: value(2, { jobs: [], count: 0 }),
        projects: value(3, { projects: [], count: 0 }),
        activity: value(4, { events: [], count: 0 }),
        references: value(5, { references: [], count: 0 }),
        presence: value(6, { ready: false }),
        sourceErrors: results.map(function (result, index) {
          return result.status === "rejected" ? index : null;
        }).filter(function (value) { return value != null; })
      };
    });
  }

  function Kicker(props) {
    return h("div", { className: "aiciv-kicker" }, props.children);
  }

  function TextButton(props) {
    return h("button", {
      type: "button",
      className: "aiciv-text-button",
      disabled: props.disabled,
      onClick: props.onClick
    }, props.children);
  }

  function HeaderWordmarkSlot() {
    useEffect(function () {
      const anchor = document.querySelector(".aiciv-wordmark-anchor");
      if (!anchor || !anchor.parentElement) return undefined;
      const siblings = Array.from(anchor.parentElement.children);
      const index = siblings.indexOf(anchor);
      const hostBrand = index >= 0 ? siblings[index + 1] : null;
      if (hostBrand) hostBrand.classList.add("aiciv-hide-when-branded");
      return function () {
        if (hostBrand) hostBrand.classList.remove("aiciv-hide-when-branded");
      };
    }, []);
    return h("span", { className: "aiciv-wordmark-anchor", "aria-label": "AiCIV" }, "AiCIV");
  }

  function HeaderBannerSlot() {
    const statusState = usePoll(function () { return SDK.api.getStatus(); }, 15000);
    const active = statusState.value && Number(statusState.value.active_sessions || 0);
    const live = active > 0 ? "● " + active + " ACTIVE " + (active === 1 ? "SESSION" : "SESSIONS") : "";
    return h("div", { className: "aiciv-dateline-rail", role: "status", "aria-live": "polite" },
      h("span", { className: "aiciv-dateline-rail__left" }, "AiCIV Inc · est. Feb 2026"),
      h("span", { className: "aiciv-dateline-rail__live" }, live),
      h("span", { className: "aiciv-dateline-rail__right" }, fullDate(new Date()))
    );
  }

  function HeaderPresenceSlot() {
    const presence = usePoll(function () { return SDK.fetchJSON(API + "/presence/ready"); }, 30000);
    const ready = Boolean(presence.value && presence.value.ready);
    const [voiceState, setVoiceState] = useState("idle");

    useEffect(function () {
      function onState(event) {
        const next = event && event.detail && event.detail.state;
        if (typeof next === "string") setVoiceState(next);
      }
      window.addEventListener("aiciv:presence:state", onState);
      return function () { window.removeEventListener("aiciv:presence:state", onState); };
    }, []);

    function startVoice() {
      window.dispatchEvent(new CustomEvent("aiciv:presence:start", {
        detail: { tokenEndpoint: API + "/presence/voice-token", surface: "hermes-web" }
      }));
    }

    let label = "Talk Live";
    if (voiceState === "connecting") label = "Connecting";
    if (voiceState === "listening") label = "Listening";
    if (voiceState === "speaking") label = "Speaking";
    if (voiceState === "muted") label = "Muted";

    return h("button", {
      type: "button",
      className: "aiciv-presence-control",
      disabled: !ready,
      onClick: startVoice,
      title: ready ? "Open the shared AiCIV Presence voice surface" : "Presence Gateway is not ready"
    }, label);
  }

  function SidebarSlot() {
    const workspace = usePoll(loadWorkspace, 15000);
    const value = workspace.value || {};
    const jobs = value.jobs && Array.isArray(value.jobs.jobs) ? value.jobs.jobs : [];
    const activeJobs = jobs.filter(function (job) { return ACTIVE.has(job.status); }).length;
    const needs = jobs.filter(function (job) { return job.status === "waiting" || job.status === "failed"; }).length;
    const sessions = value.status ? Number(value.status.active_sessions || 0) : null;

    function link(label, view) {
      return h("a", { href: objectHref(view) }, label);
    }
    function core(label, path) {
      return h("a", { href: hermesHref(path) }, label);
    }

    return h("nav", { className: "aiciv-sidebar", "aria-label": "AiCIV workspace" },
      h("div", { className: "aiciv-sidebar__section" },
        h("span", { className: "aiciv-sidebar__label" }, "Workspace"),
        link("Now", "now"),
        link("Needs You", "needs"),
        link("Results", "results"),
        link("Projects", "projects"),
        link("Activity", "activity"),
        link("References", "references")
      ),
      h("div", { className: "aiciv-sidebar__section" },
        h("span", { className: "aiciv-sidebar__label" }, "Current state"),
        h("div", { className: "aiciv-sidebar__fact" }, h("span", null, "Live sessions"), h("strong", null, sessions == null ? "—" : sessions)),
        h("div", { className: "aiciv-sidebar__fact" }, h("span", null, "Durable work"), h("strong", null, activeJobs)),
        h("div", { className: "aiciv-sidebar__fact" }, h("span", null, "Needs you"), h("strong", null, needs))
      ),
      h("div", { className: "aiciv-sidebar__section" },
        h("span", { className: "aiciv-sidebar__label" }, "Hermes substrate"),
        core("Sessions", "/sessions"),
        core("Files", "/files"),
        core("Cron", "/cron"),
        core("Skills", "/skills"),
        core("Plugins", "/plugins"),
        core("Models", "/models"),
        core("System", "/system")
      )
    );
  }

  function DisclosureSlot() {
    return h("span", { className: "aiciv-disclosure" }, "Outputs are AI-generated. Verify before acting. (EU AI Act, Art. 50)");
  }

  function ChatTopSlot() {
    const jobsState = usePoll(function () { return SDK.fetchJSON(API + "/jobs?limit=50"); }, 15000);
    const jobs = jobsState.value && Array.isArray(jobsState.value.jobs) ? jobsState.value.jobs : [];
    const active = jobs.filter(function (job) { return ACTIVE.has(job.status); }).length;
    const returned = jobs.filter(function (job) { return TERMINAL.has(job.status); }).length;
    if (!active && !returned) return null;
    return h("div", { className: "aiciv-chat-rail" },
      "Durable AiCIV work: " + active + " active · " + returned + " returned. ",
      h("a", { href: objectHref("now") }, "Open Now")
    );
  }

  function SessionsTopSlot() {
    return h("div", { className: "aiciv-sessions-context" },
      "Sessions are runtime objects. AiCIV Projects and shared References link to them without copying their conversation state. ",
      h("a", { href: objectHref("projects") }, "Open Projects")
    );
  }

  function Metric(props) {
    return h("div", { className: "aiciv-metric" },
      h("span", null, props.label),
      h("strong", null, props.value)
    );
  }

  function Receipts(props) {
    const receipts = Array.isArray(props.receipts) ? props.receipts : [];
    if (!receipts.length) return null;
    return h("div", { className: "aiciv-receipts" },
      h("span", { className: "aiciv-receipts__label" }, "Evidence and receipts"),
      receipts.slice(0, 8).map(function (receipt, index) {
        const label = receipt.label || receipt.kind || "Receipt";
        const uri = receipt.uri;
        return h("div", { key: String(index) },
          uri && /^https?:\/\//.test(uri)
            ? h("a", { href: uri, target: "_blank", rel: "noopener noreferrer" }, label)
            : h("span", null, label + (uri ? " · " + uri : ""))
        );
      })
    );
  }

  function JobItem(props) {
    const job = props.job;
    const [stopping, setStopping] = useState(false);
    const [error, setError] = useState("");
    const result = resultText(job.result);
    function requestStop() {
      setStopping(true);
      setError("");
      SDK.fetchJSON(API + "/jobs/" + encodeURIComponent(job.jobId) + "/cancel", { method: "POST" })
        .then(function () { if (props.onRefresh) props.onRefresh(); })
        .catch(function () { setError("Stop request was not accepted."); })
        .finally(function () { setStopping(false); });
    }
    const canStop = ["queued", "accepted", "running", "waiting"].indexOf(job.status) >= 0;
    return h("article", { className: "aiciv-item", id: job.jobId },
      h("div", { className: "aiciv-item__meta" },
        h("span", { className: job.status === "waiting" || job.status === "failed" ? "aiciv-status aiciv-status--attention" : "aiciv-status" }, String(job.status || "unknown").replace(/_/g, " ")),
        h("span", null, fmtTime(job.updatedAt || job.createdAt)),
        h("span", null, job.jobId || "")
      ),
      h("h3", { className: "aiciv-item__title" }, job.goal || "Durable work"),
      job.error ? h("p", { className: "aiciv-item__body aiciv-error" }, String(job.error)) : null,
      result && TERMINAL.has(job.status) ? h("p", { className: "aiciv-item__body" }, result) : null,
      h(Receipts, { receipts: job.receipts }),
      canStop ? h("div", { className: "aiciv-item__actions" },
        h(TextButton, { disabled: stopping, onClick: requestStop }, stopping ? "Requesting stop" : "Request stop")
      ) : null,
      error ? h("p", { className: "aiciv-error" }, error) : null
    );
  }

  function SessionItem(props) {
    const session = props.session;
    return h("article", { className: "aiciv-item" },
      h("div", { className: "aiciv-item__meta" },
        session.source ? h("span", null, session.source) : null,
        session.model ? h("span", null, session.model) : null,
        session.started_at ? h("span", null, fmtTime(session.started_at)) : null
      ),
      h("h3", { className: "aiciv-item__title" }, session.title || session.id || "Session"),
      h("div", { className: "aiciv-item__actions" },
        h("a", { className: "aiciv-link-button", href: hermesHref("/sessions") }, "Open Sessions")
      )
    );
  }

  function PageHead(props) {
    return h("header", { className: "aiciv-page-head" },
      h(Kicker, null, props.kicker || "AICIV WORKSPACE"),
      h("h1", null, props.title),
      h("p", null, props.description)
    );
  }

  function WorkspaceTabs(props) {
    const items = [
      ["now", "Now"],
      ["needs", "Needs You"],
      ["results", "Results"],
      ["projects", "Projects"],
      ["activity", "Activity"],
      ["references", "References"],
      ["presence", "Presence"]
    ];
    return h("nav", { className: "aiciv-tabs", "aria-label": "AiCIV workspace sections" },
      items.map(function (item) {
        return h("a", {
          key: item[0],
          href: objectHref(item[0]),
          "aria-current": props.current === item[0] ? "page" : undefined
        }, item[1]);
      })
    );
  }

  function NowView(props) {
    const data = props.data;
    const jobs = data.jobs && Array.isArray(data.jobs.jobs) ? data.jobs.jobs : [];
    const sessions = data.sessions && Array.isArray(data.sessions.sessions) ? data.sessions.sessions : [];
    const activeJobs = jobs.filter(function (job) { return ACTIVE.has(job.status); });
    const needs = jobs.filter(function (job) { return job.status === "waiting" || job.status === "failed"; });
    const returned = jobs.filter(function (job) { return TERMINAL.has(job.status); });
    const activeSessions = data.status ? Number(data.status.active_sessions || 0) : 0;

    return h(React.Fragment, null,
      h(PageHead, {
        title: "What is the civilization doing now?",
        description: "Live Hermes runtime state beside durable AiCIV work. Meaning first. Raw machinery remains one click away."
      }),
      h("div", { className: "aiciv-metrics", "aria-label": "Current AiCIV state" },
        h(Metric, { label: "Live sessions", value: activeSessions }),
        h(Metric, { label: "Durable work", value: activeJobs.length }),
        h(Metric, { label: "Needs you", value: needs.length }),
        h(Metric, { label: "Returned", value: returned.length })
      ),
      h("section", { className: "aiciv-section" },
        h("div", { className: "aiciv-section__head" }, h("h2", null, "Working now"), h("a", { href: objectHref("results") }, "Returned work")),
        activeJobs.length
          ? h("div", { className: "aiciv-list" }, activeJobs.slice(0, 8).map(function (job) { return h(JobItem, { key: job.jobId, job: job, onRefresh: props.onRefresh }); }))
          : h("p", { className: "aiciv-empty" }, "No durable Presence jobs are active. Hermes sessions can still be working independently below.")
      ),
      h("section", { className: "aiciv-section" },
        h("div", { className: "aiciv-section__head" }, h("h2", null, "Recent Hermes sessions"), h("a", { href: hermesHref("/sessions") }, "All sessions")),
        sessions.length
          ? h("div", { className: "aiciv-list" }, sessions.slice(0, 6).map(function (session) { return h(SessionItem, { key: session.id, session: session }); }))
          : h("p", { className: "aiciv-empty" }, "No recent Hermes sessions were returned by the runtime.")
      )
    );
  }

  function JobsView(props) {
    const jobs = props.data.jobs && Array.isArray(props.data.jobs.jobs) ? props.data.jobs.jobs : [];
    const needsMode = props.mode === "needs";
    const filtered = needsMode
      ? jobs.filter(function (job) { return job.status === "waiting" || job.status === "failed"; })
      : jobs.filter(function (job) { return TERMINAL.has(job.status); });
    return h(React.Fragment, null,
      h(PageHead, {
        kicker: needsMode ? "NEEDS YOU" : "RESULTS",
        title: needsMode ? "Judgment belongs here." : "Returned work stays findable.",
        description: needsMode
          ? "Waiting and failed durable work is surfaced explicitly. Delivery, execution and completion remain separate states."
          : "Terminal Presence jobs are kept separate from conversation history so results and receipts do not disappear into old chat."
      }),
      h("section", { className: "aiciv-section" },
        filtered.length
          ? h("div", { className: "aiciv-list" }, filtered.map(function (job) { return h(JobItem, { key: job.jobId, job: job, onRefresh: props.onRefresh }); }))
          : h("p", { className: "aiciv-empty" }, needsMode ? "Nothing currently needs human attention." : "No durable results have returned yet.")
      )
    );
  }

  function ProjectsView(props) {
    const projects = props.data.projects && Array.isArray(props.data.projects.projects) ? props.data.projects.projects : [];
    const [title, setTitle] = useState("");
    const [goal, setGoal] = useState("");
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    function createProject(event) {
      event.preventDefault();
      if (!title.trim() || !goal.trim()) return;
      setSaving(true);
      setError("");
      SDK.fetchJSON(API + "/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), goal: goal.trim() })
      }).then(function () {
        setTitle("");
        setGoal("");
        props.onRefresh();
      }).catch(function () {
        setError("Project was not saved.");
      }).finally(function () { setSaving(false); });
    }
    return h(React.Fragment, null,
      h(PageHead, {
        kicker: "PROJECTS",
        title: "Work has a home beyond the chat thread.",
        description: "Projects store goals and relationships. Hermes sessions, Presence jobs, files and evidence remain authoritative in their source systems."
      }),
      h("form", { className: "aiciv-form", onSubmit: createProject },
        h("label", null, "Project title", h("input", { value: title, onChange: function (e) { setTitle(e.target.value); }, maxLength: 240 })),
        h("label", null, "Goal", h("textarea", { value: goal, onChange: function (e) { setGoal(e.target.value); }, maxLength: 8000 })),
        h(TextButton, { disabled: saving || !title.trim() || !goal.trim() }, saving ? "Saving" : "Create project"),
        error ? h("p", { className: "aiciv-error" }, error) : null
      ),
      h("section", { className: "aiciv-section" },
        projects.length
          ? h("div", { className: "aiciv-list" }, projects.map(function (project) {
              return h("article", { className: "aiciv-item", key: project.projectId },
                h("div", { className: "aiciv-item__meta" }, h("span", null, project.status || "active"), h("span", null, fmtTime(project.updatedAt)), h("span", null, project.projectId)),
                h("h3", { className: "aiciv-item__title" }, project.title),
                h("p", { className: "aiciv-item__body" }, project.goal),
                Array.isArray(project.links) && project.links.length
                  ? h("p", { className: "aiciv-item__body" }, project.links.length + " linked authoritative object" + (project.links.length === 1 ? "" : "s"))
                  : null
              );
            }))
          : h("p", { className: "aiciv-empty" }, "No AiCIV Projects yet. Create one when a body of work should survive the current session.")
      )
    );
  }

  function ActivityView(props) {
    const events = props.data.activity && Array.isArray(props.data.activity.events) ? props.data.activity.events : [];
    return h(React.Fragment, null,
      h(PageHead, {
        kicker: "ACTIVITY",
        title: "The record compounds.",
        description: "This stream records AiCIV workspace changes. It is not a substitute for Hermes logs or Presence receipts; it links you back to the meaning of those events."
      }),
      h("section", { className: "aiciv-section" },
        events.length
          ? h("div", { className: "aiciv-list" }, events.map(function (event) {
              return h("article", { className: "aiciv-item", key: event.id },
                h("div", { className: "aiciv-item__meta" }, h("span", null, event.kind), h("span", null, fmtTime(event.createdAt)), h("span", null, event.actor || "")),
                h("h3", { className: "aiciv-item__title" }, event.summary || event.objectRef),
                event.objectRef ? h("p", { className: "aiciv-item__body" }, event.objectRef) : null
              );
            }))
          : h("p", { className: "aiciv-empty" }, "No AiCIV workspace activity has been filed yet.")
      )
    );
  }

  function ReferencesView(props) {
    const refs = props.data.references && Array.isArray(props.data.references.references) ? props.data.references.references : [];
    return h(React.Fragment, null,
      h(PageHead, {
        kicker: "REFERENCES",
        title: "Shared things the civilization should not lose.",
        description: "References are durable links to authoritative objects. Saving a reference does not copy or complete the underlying work."
      }),
      h("section", { className: "aiciv-section" },
        refs.length
          ? h("div", { className: "aiciv-list" }, refs.map(function (ref) {
              return h("article", { className: "aiciv-item", key: ref.ref },
                h("div", { className: "aiciv-item__meta" }, h("span", null, ref.kind), h("span", null, fmtTime(ref.savedAt))),
                h("h3", { className: "aiciv-item__title" }, ref.label || ref.ref),
                ref.note ? h("p", { className: "aiciv-item__body" }, ref.note) : null,
                h("p", { className: "aiciv-item__body" }, ref.ref)
              );
            }))
          : h("p", { className: "aiciv-empty" }, "No shared References have been saved yet.")
      )
    );
  }

  function PresenceView(props) {
    const ready = Boolean(props.data.presence && props.data.presence.ready);
    function requestVoice() {
      window.dispatchEvent(new CustomEvent("aiciv:presence:start", {
        detail: { tokenEndpoint: API + "/presence/voice-token", surface: "hermes-web" }
      }));
    }
    return h(React.Fragment, null,
      h(PageHead, {
        kicker: "PRESENCE",
        title: "One relationship. Multiple bodies.",
        description: "Hermes Web identifies as a realtime surface. Durable continuity belongs to the human↔AiCIV relationship and is shared with Portal, mobile, Reachy and future bodies."
      }),
      h("section", { className: "aiciv-section" },
        h("div", { className: "aiciv-list" },
          h("article", { className: "aiciv-item" },
            h("div", { className: "aiciv-item__meta" }, h("span", null, ready ? "Presence Gateway ready" : "Presence Gateway unavailable")),
            h("h3", { className: "aiciv-item__title" }, "Talk Live"),
            h("p", { className: "aiciv-item__body" }, "Voice startup is an explicit client handoff. The browser receives only a short-lived conversation credential. Provider and gateway secrets remain server-side."),
            h("div", { className: "aiciv-item__actions" }, h(TextButton, { disabled: !ready, onClick: requestVoice }, "Talk Live"))
          )
        )
      )
    );
  }

  function WorkspacePage() {
    const [refreshNonce, setRefreshNonce] = useState(0);
    const workspace = usePoll(loadWorkspace, 10000 + refreshNonce * 0);
    const data = workspace.value || {
      status: null,
      sessions: { sessions: [], total: 0 },
      jobs: { jobs: [], count: 0 },
      projects: { projects: [], count: 0 },
      activity: { events: [], count: 0 },
      references: { references: [], count: 0 },
      presence: { ready: false },
      sourceErrors: []
    };
    const view = new URLSearchParams(window.location.search).get("aiciv") || "now";
    function refresh() { setRefreshNonce(function (value) { return value + 1; }); window.location.reload(); }

    let content;
    if (view === "needs") content = h(JobsView, { mode: "needs", data: data, onRefresh: refresh });
    else if (view === "results") content = h(JobsView, { mode: "results", data: data, onRefresh: refresh });
    else if (view === "projects") content = h(ProjectsView, { data: data, onRefresh: refresh });
    else if (view === "activity") content = h(ActivityView, { data: data });
    else if (view === "references") content = h(ReferencesView, { data: data });
    else if (view === "presence") content = h(PresenceView, { data: data });
    else content = h(NowView, { data: data, onRefresh: refresh });

    return h("div", { className: "aiciv-root" },
      h(WorkspaceTabs, { current: view }),
      data.sourceErrors && data.sourceErrors.length
        ? h("p", { className: "aiciv-error" }, "One or more runtime sources did not answer. Last known or empty state is shown without inventing data.")
        : null,
      workspace.loading && !workspace.value ? h("p", { className: "aiciv-empty" }, "Building the current record.") : content
    );
  }

  REGISTRY.register("aiciv-workspace", WorkspacePage);
  REGISTRY.registerSlot("aiciv-workspace", "header-left", HeaderWordmarkSlot);
  REGISTRY.registerSlot("aiciv-workspace", "header-right", HeaderPresenceSlot);
  REGISTRY.registerSlot("aiciv-workspace", "header-banner", HeaderBannerSlot);
  REGISTRY.registerSlot("aiciv-workspace", "sidebar", SidebarSlot);
  REGISTRY.registerSlot("aiciv-workspace", "chat:top", ChatTopSlot);
  REGISTRY.registerSlot("aiciv-workspace", "sessions:top", SessionsTopSlot);
  REGISTRY.registerSlot("aiciv-workspace", "footer-left", DisclosureSlot);
})();
