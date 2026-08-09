/* AiCIV semantic Teams — meaning-first projection over Hermes profiles + Kanban work. */
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
  const PROFILE_API = "/api/plugins/kanban/profiles";
  const BOARD_API = "/api/plugins/kanban/board";
  const ACTIVE = new Set(["triage", "todo", "scheduled", "ready", "running", "blocked", "review"]);

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

  function flattenBoard(board) {
    const result = [];
    const columns = board && Array.isArray(board.columns) ? board.columns : [];
    columns.forEach(function (column) {
      const status = column && typeof column.name === "string" ? column.name : "todo";
      const tasks = column && Array.isArray(column.tasks) ? column.tasks : [];
      tasks.forEach(function (task) {
        if (!task || typeof task !== "object") return;
        result.push(Object.assign({ status: status }, task));
      });
    });
    return result;
  }

  function useTeamState() {
    const [state, setState] = useState({ loading: true, profiles: [], board: null, error: null });
    useEffect(function () {
      let disposed = false;
      let timer = null;

      async function refresh() {
        try {
          const values = await Promise.all([
            SDK.fetchJSON(PROFILE_API),
            SDK.fetchJSON(BOARD_API)
          ]);
          if (disposed) return;
          setState({
            loading: false,
            profiles: values[0] && Array.isArray(values[0].profiles) ? values[0].profiles : [],
            board: values[1] || null,
            error: null
          });
        } catch (error) {
          if (!disposed) setState(function (previous) {
            return Object.assign({}, previous, { loading: false, error: error });
          });
        }
      }

      refresh();
      timer = window.setInterval(refresh, 7000);
      return function () {
        disposed = true;
        if (timer) window.clearInterval(timer);
      };
    }, []);
    return state;
  }

  function taskRank(status) {
    return ({ blocked: 0, running: 1, review: 2, ready: 3, scheduled: 4, todo: 5, triage: 6 })[status] ?? 9;
  }

  function semanticState(tasks) {
    if (tasks.some(function (task) { return task.status === "blocked"; })) return "Needs attention";
    if (tasks.some(function (task) { return task.status === "running"; })) return "Working";
    if (tasks.some(function (task) { return task.status === "review"; })) return "Ready for review";
    if (tasks.some(function (task) { return task.status === "ready"; })) return "Ready";
    if (tasks.some(function (task) { return task.status === "scheduled"; })) return "Scheduled";
    if (tasks.length) return "Waiting";
    return "Available";
  }

  function heartbeat(task) {
    const raw = task && task.last_heartbeat_at;
    if (!raw) return "";
    const date = new Date(raw < 100000000000 ? raw * 1000 : raw);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleString();
  }

  function teamRows(profiles, board) {
    const tasks = flattenBoard(board).filter(function (task) { return ACTIVE.has(task.status); });
    const names = new Set();
    const profileMap = new Map();
    profiles.forEach(function (profile) {
      if (!profile || !profile.name) return;
      names.add(profile.name);
      profileMap.set(profile.name, profile);
    });
    tasks.forEach(function (task) {
      if (task.assignee) names.add(task.assignee);
    });

    return Array.from(names).sort().map(function (name) {
      const profile = profileMap.get(name) || { name: name, description: "", skill_count: 0 };
      const owned = tasks
        .filter(function (task) { return task.assignee === name; })
        .sort(function (a, b) { return taskRank(a.status) - taskRank(b.status); });
      const focus = owned[0] || null;
      return {
        name: name,
        profile: profile,
        tasks: owned,
        focus: focus,
        state: semanticState(owned)
      };
    }).sort(function (a, b) {
      const rank = { "Needs attention": 0, "Working": 1, "Ready for review": 2, "Ready": 3, "Scheduled": 4, "Waiting": 5, "Available": 6 };
      return (rank[a.state] ?? 9) - (rank[b.state] ?? 9) || a.name.localeCompare(b.name);
    });
  }

  function ProfileRow(props) {
    const row = props.row;
    const profile = row.profile;
    const focus = row.focus;
    return h("article", { className: "aiciv-item", "data-profile": row.name },
      h("div", { className: "aiciv-item__meta" },
        h("span", null, row.state),
        h("span", null, "profile:" + row.name),
        profile.model ? h("span", null, profile.model) : null,
        profile.provider ? h("span", null, profile.provider) : null,
        profile.skill_count != null ? h("span", null, profile.skill_count + " skills") : null
      ),
      h("h3", { className: "aiciv-item__title" }, row.name),
      profile.description ? h("p", { className: "aiciv-item__body" }, profile.description) : null,
      focus
        ? h("div", { className: "aiciv-team-focus" },
            h("strong", null, "Current focus: "),
            h("span", null, focus.title || focus.id),
            h("span", null, " · task:" + focus.id),
            focus.last_heartbeat_at ? h("span", null, " · heartbeat " + heartbeat(focus)) : null
          )
        : h("p", { className: "aiciv-item__body" }, "No active Hermes task is assigned. This does not imply the profile is offline."),
      row.tasks.length > 1
        ? h("div", { className: "aiciv-receipts" },
            h("span", { className: "aiciv-receipts__label" }, "Other work"),
            row.tasks.slice(1, 5).map(function (task) {
              return h("span", { key: task.id }, task.status + " · task:" + task.id);
            })
          )
        : null
    );
  }

  function TeamsProjection() {
    const view = currentView();
    const state = useTeamState();
    const rows = useMemo(function () {
      return state.board ? teamRows(state.profiles, state.board) : [];
    }, [state.profiles, state.board]);

    if (view !== "teams" && view !== "now") return null;
    if (view === "now") {
      if (state.loading || state.error || rows.length === 0) return null;
      const working = rows.filter(function (row) { return row.state === "Working"; }).length;
      const attention = rows.filter(function (row) { return row.state === "Needs attention"; }).length;
      const ready = rows.filter(function (row) { return row.state === "Ready for review" || row.state === "Ready"; }).length;
      return h("section", { className: "aiciv-section", "data-aiciv-authority": "hermes-profiles-kanban" },
        h("div", { className: "aiciv-section__head" },
          h("h2", null, "Civilization"),
          h("a", { href: BASE + "/?aiciv=teams" }, "Open Teams →")
        ),
        h("div", { className: "aiciv-item__meta" },
          h("span", null, working + " working"),
          h("span", null, attention + " needs attention"),
          h("span", null, ready + " ready")
        )
      );
    }

    return h("section", { className: "aiciv-section", "data-aiciv-authority": "hermes-profiles-kanban" },
      h("div", { className: "aiciv-section__head" },
        h("h2", null, "Teams"),
        h("a", { href: BASE + "/kanban" }, "Open raw Hermes work →")
      ),
      h("p", { className: "aiciv-item__body" },
        "Semantic state is derived from installed Hermes profiles and authoritative Kanban task/worker evidence. Profile existence alone is never treated as online presence."
      ),
      state.error
        ? h("p", { className: "aiciv-error" }, "Hermes team state is unavailable. AiCIV will not invent agent activity.")
        : state.loading
          ? h("p", { className: "aiciv-empty" }, "Reading Hermes profiles and active work.")
          : rows.length
            ? h("div", { className: "aiciv-list" }, rows.map(function (row) {
                return h(ProfileRow, { key: row.name, row: row });
              }))
            : h("p", { className: "aiciv-empty" }, "No Hermes profiles are currently discoverable.")
    );
  }

  function TeamsSidebarLink() {
    return h("a", { className: "aiciv-sidebar-link", href: BASE + "/?aiciv=teams" }, "Teams");
  }

  REGISTRY.registerSlot("aiciv-semantic-teams", "post-main", TeamsProjection);
  REGISTRY.registerSlot("aiciv-semantic-teams", "sidebar", TeamsSidebarLink);
})();
