import { useCallback, useEffect, useRef, useState } from "react";

const api = async (path, opts = {}) => {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

function Login({ onLogin }) {
  const [users, setUsers] = useState([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [parentEmail, setParentEmail] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/users").then(setUsers).catch(() => setUsers([]));
  }, []);

  const create = async (e) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !parentEmail.trim()) return;
    try {
      const uid = "u" + Date.now().toString(36);
      await api("/users/upsert", {
        method: "POST",
        body: JSON.stringify({
          google_id: uid,
          email,
          name,
          parent_email: parentEmail,
        }),
      });
      onLogin({ user_id: uid, name, email });
    } catch (err) {
      setError(String(err));
    }
  };

  return (
    <div className="login">
      <div className="card">
        <h1>🛡️ Aegis</h1>
        <p className="sub">Child Chat Guardian — pick a profile or create one</p>
        {users.length > 0 && (
          <>
            <h3>Existing profiles</h3>
            <div className="user-list">
              {users.map((u) => (
                <button key={u.user_id} className="user-btn" onClick={() => onLogin(u)}>
                  {u.name}
                </button>
              ))}
            </div>
          </>
        )}
        <h3>New profile</h3>
        <form onSubmit={create}>
          <input placeholder="Child name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Child email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder="Parent email (gets alerts)" value={parentEmail} onChange={(e) => setParentEmail(e.target.value)} />
          <button type="submit" className="primary">Create & start chatting</button>
        </form>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}

function DecisionBadge({ d }) {
  if (!d) return null;
  const cls = d.action === "block" ? "badge-block" : d.action === "warn" ? "badge-warn" : "badge-ok";
  return (
    <span className={`badge ${cls}`} title={d.reason || ""}>
      {d.action} · risk {d.risk_score}
    </span>
  );
}

function Chat({ me, onLogout }) {
  const [contacts, setContacts] = useState([]);
  const [other, setOther] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [alerts, setAlerts] = useState([]);
  const [showAlerts, setShowAlerts] = useState(false);
  const [status, setStatus] = useState("connecting");
  const wsRef = useRef(null);
  const bottomRef = useRef(null);

  const loadMessages = useCallback(async (o) => {
    if (!o) return;
    try {
      const list = await api(`/chat/history/${me.user_id}/${o.user_id}`);
      setMessages(list.map((m) => ({ ...m, incoming: m.sender_id !== me.user_id })));
    } catch {
      setMessages([]);
    }
  }, [me.user_id]);

  useEffect(() => {
    api("/users").then(setContacts).catch(() => {});
  }, []);

  useEffect(() => {
    loadMessages(other);
  }, [other, loadMessages]);

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws/chat?user_id=${me.user_id}`);
    wsRef.current = ws;
    ws.onopen = () => setStatus("online");
    ws.onclose = () => setStatus("offline");
    ws.onerror = () => setStatus("error");
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === "message") {
        setMessages((m) => [...m, { text: data.text, incoming: true, sender_id: data.sender_id, risk_score: data.risk_score }]);
      } else if (data.type === "decision") {
        setMessages((m) => {
          const last = [...m];
          last[last.length - 1] = { ...last[last.length - 1], decision: data };
          return last;
        });
      }
    };
    const hb = setInterval(() => {
      fetch(`/users/heartbeat?user_id=${me.user_id}`, { method: "POST" }).catch(() => {});
    }, 60000);
    return () => {
      ws.close();
      clearInterval(hb);
    };
  }, [me.user_id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || !other || wsRef.current?.readyState !== WebSocket.OPEN) return;
    setMessages((m) => [...m, { text, incoming: false, pending: true }]);
    setInput("");
    wsRef.current.send(JSON.stringify({ type: "message", recipient_id: other.user_id, text }));
  };

  const openAlerts = async () => {
    setAlerts(await api(`/alerts/${me.user_id}`));
    setShowAlerts(!showAlerts);
  };

  return (
    <div className="chat">
      <header>
        <h1>🛡️ Aegis</h1>
        <span>You: <b>{me.name}</b> · <span className={`dot ${status}`} /> {status}</span>
        <div className="header-actions">
          <button className="ghost" onClick={openAlerts}>Parent alerts ({alerts.length})</button>
          <button className="ghost" onClick={onLogout}>Logout</button>
        </div>
      </header>

      <div className="body">
        <aside className="contacts">
          <h3>Contacts</h3>
          {contacts.filter((c) => c.user_id !== me.user_id).map((c) => (
            <button
              key={c.user_id}
              className={`contact ${other?.user_id === c.user_id ? "active" : ""}`}
              onClick={() => setOther(c)}
            >
              {c.name}
            </button>
          ))}
          {contacts.length <= 1 && <p className="hint">Open a second browser tab with another profile to chat.</p>}
        </aside>

        <main className="messages">
          {!other ? (
            <p className="hint center">Select a contact to start chatting</p>
          ) : (
            <>
              <div className="thread">
                {messages.map((m, i) => (
                  <div key={i} className={`bubble ${m.incoming ? "in" : "out"}`}>
                    <span className="text">{m.text}</span>
                    <div className="meta">
                      <DecisionBadge d={m.decision} />
                      {m.pending && !m.decision && <span className="pending">checking…</span>}
                    </div>
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
              <form className="composer" onSubmit={send}>
                <input
                  placeholder="Type a message… (Aegis checks it before delivery)"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                />
                <button type="submit" className="primary">Send</button>
              </form>
            </>
          )}
        </main>

        {showAlerts && (
          <aside className="alerts">
            <h3>Parent alerts for {me.name}</h3>
            {alerts.length === 0 && <p className="hint">No alerts yet.</p>}
            {alerts.map((a, i) => (
              <div key={i} className={`alert ${a.alert_type}`}>
                <b>{a.alert_type}</b>
                <p>{a.message_text || a.reason}</p>
                <small>{new Date(a.created_at).toLocaleString()}</small>
              </div>
            ))}
          </aside>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [me, setMe] = useState(() => JSON.parse(sessionStorage.getItem("aegis_user") || "null"));
  const login = (u) => {
    sessionStorage.setItem("aegis_user", JSON.stringify(u));
    setMe(u);
  };
  const logout = () => {
    sessionStorage.removeItem("aegis_user");
    setMe(null);
  };
  return me ? <Chat me={me} onLogout={logout} /> : <Login onLogin={login} />;
}
