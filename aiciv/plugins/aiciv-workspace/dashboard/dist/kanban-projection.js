/* AiCIV projection of authoritative Hermes Kanban state. Read-only by design. */
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
  const BOARD_API = "/api/plugins/kanban/board";
  const EVENTS_WS = "/api/plugins/kanban/events";
  const ACTIVE_STATUSES = new Set(["triage", "todo", "scheduled", "ready", "running", "blocked", "review"]);

  function currentAiCivView() {
    return new URLSearchParams(window.location.search).get("aiciv") || "now";
  }

  function flattenBoard(board) {
    const columns = board && Array.isArray(board.columns) ? board.columns : [];
    const tasks = [];
    columns.forEach(function (column) {
      const status = column && typeof column.name === "string" ? column.name : "todo";
      const items = column && Array.isArray(column.tasks) ? column.tasks : [];
      items.forEach(function (task) {
        tasks.push(Object.assign({ status: status }, task || {}));
      });
    });
    return tasks;
  }

  function taskTitle(task) {
    return task.title || task.name || task.subject || task.id || "Untitled task";
  }

  function taskRef(task) {
    return task && task.id ? "task:" + task.id : "task:unknown";
  }

  function taskOwner(task) {
    return task.assignee || task.profile || task.tenant || "";
  }

  function taskTime(task) {
    const raw = task.updated_at || task.updatedAt || task.created_at || task.createdAt;
    if (!raw) return "";
    const date = typeof raw === "number" ? new Date(raw < 100000000000 ? raw * 1000 : raw) : new Date(raw);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
  }

  function eventTime(event) {
    const raw = event && event.created_at;
    if (!raw) return "";
    const date = typeof raw === "number" ? new Date(raw < 100000000000 ? raw * 1000 : raw) : new Date(raw);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
  }

  function statusMeaning(status) {
    const map = {
      triage: "Triage",
      todo: "Ready",
      scheduled: "Scheduled",
      ready: "Ready",
      running: "Working",
      blocked: "Needs attention",
      review: "Ready for review",
      done: "Done",
      archived: "Archived"
    };
    return map[status] || status || "Unknown";
  }

  function eventMeaning(event) {
    if (!event) return "Kanban changed";
    const kind = String(event.kind || "task_event").replaceAll("_", " ");
    return kind.charAt(0).toUpperCase() + kind.slice(1);
  }

  function useKanbanProjection() {
    const [state, setState] = useState({
      loading: true,
      board: null,
      events: [],
      connected: false,
      error: null
    });

    useEffect(function () {
      let disposed = false;
      let socket = null;
      let reconnectTimer = null;
      let refreshTimer = null;
      let reconnectDelay = 1000;

      function setPartial(patch) {
        if (!disposed) setState(function (previous) { return Object.assign({}, previous, patch); });
      }

      async function refreshBoard() {
        try {
          const board = await SDK.fetchJSON(BOARD_API);
          setPartial({ board: board, loading: false, error: null });
          return board;
        } catch (error) {
          setPartial({ loading: false, error: error });
          throw error;
        }
      }

      function scheduleBoardRefresh() {
        if (refreshTimer) return;
        refreshTimer = window.setTimeout(function () {
          refreshTimer = null;
          refreshBoard().catch(function () {});
        }, 250);
      }

      function mergeEvents(incoming) {
        if (!Array.isArray(incoming) || !incoming.length) return;
        setState(function (previous) {
          const byId = new Map();
          previous.events.forEach(function (event) { byId.set(Number(event.id), event); });
          incoming.forEach(function (event) { byId.set(Number(event.id), event); });
          const events = Array.from(byId.values())
            .filter(function (event) { return Number.isFinite(Number(event.id)); })
            .sort(function (a, b) { return Number(b.id) - Number(a.id); })
            .slice(0, 80);
          return Object.assign({}, previous, { events: events });
        });
      }

      async function connect(board) {
        if (disposed) return;
        const latest = Number(board && board.latest_event_id || 0);
        const since = Math.max(0, latest - 50);
        try {
          const url = await SDK.buildWsUrl(EVENTS_WS, { since: String(since) });
          if (disposed) return;
          socket = new WebSocket(url);
          socket.onopen = function () {
            reconnectDelay = 1000;
            setPartial({ connected: true });
          };
          socket.onmessage = function (message) {
            try {
              const payload = JSON.parse(message.data);
              mergeEvents(payload.events);
              if (Array.isArray(payload.events) && payload.events.length) scheduleBoardRefresh();
            } catch (_) {
              // A malformed event frame is ignored; authoritative board refresh remains available.
            }
          };
          socket.onerror = function () {
            setPartial({ connected: false });
          };
          socket.onclose = function () {
            setPartial({ connected: false });
            if (disposed) return;
            reconnectTimer = window.setTimeout(function () {
              refreshBoard()
                .then(connect)
                .catch(function () {});
            }, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, 15000);
          };
        } catch (error) {
          setPartial({ connected: false, error: error });
        }
      }

      refreshBoard()
        .then(connect)
        .catch(function () {});

      return function () {
        disposed = true;
        if (refreshTimer) window.clearTimeout(refreshTimer);
        if (reconnectTimer) window.clearTimeout(reconnectTimer);
        if (socket) {
          socket.onclose = null;
          socket.close();
        }
      };
    }, []);

    return state;
  }

  function TaskRow(props) {
    const task = props.task;
    const owner = taskOwner(task);
    return h("article", { className: "aiciv-item" },
      h("div", { className: "aiciv-item__meta" },
        h("span", null, statusMeaning(task.status)),
        owner ? h("span", null, owner) : null,
        taskTime(task) ? h("span", null, taskTime(task)) : null,
        h("span", null, taskRef(task))
      ),
      h("h3", { className: "aiciv-item__title" }, taskTitle(task)),
      task.latest_summary
        ? h("p", { className: "aiciv-item__body" }, task.latest_summary)
        : task.description
          ? h("p", { className: "aiciv-item__body" }, String(task.description).slice(0, 280))
          : null
    );
  }

  function NowKanban(props) {
    const tasks = useMemo(function () {
      return flattenBoard(props.board)
        .filter(function (task) { return ACTIVE_STATUSES.has(task.status); })
        .sort(function (a, b) {
          const rank = { blocked: 0, running: 1, review: 2, ready: 3, scheduled: 4, triage: 5, todo: 6 };
          return (rank[a.status] ?? 9) - (rank[b.status] ?? 9);
        });
    }, [props.board]);

    const running = tasks.filter(function (task) { return task.status === "running"; }).length;
    const blocked = tasks.filter(function (task) { return task.status === "blocked"; }).length;
    const review = tasks.filter(function (task) { return task.status === "review"; }).length;

    return h("section", { className: "aiciv-section", "data-aiciv-authority": "hermes-kanban" },
      h("div", { className: "aiciv-section__head" },
        h("h2", null, "Hermes Work"),
        h("a", { href: BASE + "/kanban" }, "Open authoritative board →")
      ),
      h("div", { className: "aiciv-item__meta" },
        h("span", null, running + " working"),
        h("span", null, blocked + " needs attention"),
        h("span", null, review + " ready for review"),
        h("span", null, props.connected ? "live events connected" : "board snapshot")
      ),
      tasks.length
        ? h("div", { className: "aiciv-list" }, tasks.slice(0, 8).map(function (task) {
            return h(TaskRow, { key: task.id || taskRef(task), task: task });
          }))
        : h("p", { className: "aiciv-empty" }, "Hermes Kanban has no active tasks on the current board.")
    );
  }

  function ActivityKanban(props) {
    return h("section", { className: "aiciv-section", "data-aiciv-authority": "hermes-task-events" },
      h("div", { className: "aiciv-section__head" },
        h("h2", null, "Hermes Task Activity"),
        h("a", { href: BASE + "/kanban" }, "Open authoritative board →")
      ),
      props.events.length
        ? h("div", { className: "aiciv-list" }, props.events.slice(0, 20).map(function (event) {
            return h("article", { className: "aiciv-item", key: event.id },
              h("div", { className: "aiciv-item__meta" },
                h("span", null, "Hermes Kanban"),
                eventTime(event) ? h("span", null, eventTime(event)) : null,
                event.task_id ? h("span", null, "task:" + event.task_id) : null,
                event.run_id ? h("span", null, "run:" + event.run_id) : null
              ),
              h("h3", { className: "aiciv-item__title" }, eventMeaning(event))
            );
          }))
        : h("p", { className: "aiciv-empty" }, props.connected
            ? "No recent Hermes task events were returned."
            : "Connecting to the authoritative Hermes task event stream.")
    );
  }

  function KanbanProjection() {
    const view = currentAiCivView();
    const state = useKanbanProjection();
    if (view !== "now" && view !== "activity") return null;
    if (state.loading && !state.board) {
      return h("section", { className: "aiciv-section" },
        h("p", { className: "aiciv-empty" }, "Reading authoritative Hermes work state.")
      );
    }
    if (!state.board) {
      return h("section", { className: "aiciv-section" },
        h("p", { className: "aiciv-error" }, "Hermes Kanban did not answer. AiCIV will not invent task state.")
      );
    }
    if (view === "activity") return h(ActivityKanban, { events: state.events, connected: state.connected });
    return h(NowKanban, { board: state.board, connected: state.connected });
  }

  REGISTRY.registerSlot("aiciv-kanban-projection", "post-main", KanbanProjection);
})();
