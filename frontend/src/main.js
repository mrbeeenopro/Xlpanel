import './styles.css';
import { api, post, patch, del } from './api';

const app = document.getElementById('app');

const state = {
  config: null,
  session: null,
  route: 'dashboard',
  loginToken: '',
  registerToken: '',
  message: '',
  serverData: null,
};

function setMessage(message, ok = false) {
  state.message = { text: message, ok };
}

function clearMessage() {
  state.message = null;
}

function messageHtml() {
  if (!state.message) return '';
  return `<p class="message ${state.message.ok ? 'good' : ''}">${state.message.text}</p>`;
}

function shell(content) {
  app.innerHTML = `<div class="container">${content}</div>`;
}

async function boot() {
  try {
    state.config = await api('/api/public/config');
    state.session = await api('/api/auth/session');
  } catch (err) {
    shell(`<div class="card"><h2>Startup error</h2><p>${err.message}</p></div>`);
    return;
  }

  render();
}

function loadTurnstileIfNeeded() {
  if (!state.config.turnstile.enable) return;
  if (window.turnstile) return;
  const script = document.createElement('script');
  script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
  script.defer = true;
  script.onload = () => renderCaptcha();
  document.head.appendChild(script);
}

function renderCaptcha() {
  if (!window.turnstile || !state.config.turnstile.enable) return;
  const loginEl = document.getElementById('turnstile-login');
  if (loginEl && !loginEl.dataset.rendered) {
    loginEl.dataset.rendered = '1';
    window.turnstile.render(loginEl, {
      sitekey: state.config.turnstile.site_key,
      callback: (token) => { state.loginToken = token; },
    });
  }

  const registerEl = document.getElementById('turnstile-register');
  if (registerEl && !registerEl.dataset.rendered) {
    registerEl.dataset.rendered = '1';
    window.turnstile.render(registerEl, {
      sitekey: state.config.turnstile.site_key,
      callback: (token) => { state.registerToken = token; },
    });
  }
}

function authView() {
  shell(`
    <div class="card">
      <h1>${state.config.name}</h1>
      <small>API-only backend + Vite frontend</small>
      <div class="row" style="margin-top:14px">
        <div class="col card">
          <h3>Login</h3>
          <form id="login-form">
            <input name="user" placeholder="Username" required />
            <div style="height:8px"></div>
            <input name="passwd" type="password" placeholder="Password" required />
            <div style="height:8px"></div>
            ${state.config.turnstile.enable ? '<div id="turnstile-login"></div><div style="height:8px"></div>' : ''}
            <button>Sign In</button>
          </form>
        </div>
        <div class="col card">
          <h3>Register</h3>
          <form id="register-form">
            <input name="user" placeholder="Username" required />
            <div style="height:8px"></div>
            <input name="email" type="email" placeholder="Email" required />
            <div style="height:8px"></div>
            <input name="passwd" type="password" placeholder="Password" required />
            <div style="height:8px"></div>
            <input name="cpasswd" type="password" placeholder="Confirm Password" required />
            <div style="height:8px"></div>
            ${state.config.turnstile.enable ? '<div id="turnstile-register"></div><div style="height:8px"></div>' : ''}
            <button>Create account</button>
          </form>
        </div>
        <div class="col card">
          <h3>Forgot Password</h3>
          <form id="forgot-form">
            <input name="email" type="email" placeholder="Email" required />
            <div style="height:8px"></div>
            <button>Send reset email</button>
          </form>
          ${state.config.features.verifyUser ? `
          <div style="height:18px"></div>
          <h3>Verify Account</h3>
          <form id="verify-form">
            <input name="user" placeholder="Username" required />
            <div style="height:8px"></div>
            <input name="code" placeholder="Verify code" required />
            <div style="height:8px"></div>
            <button>Verify</button>
          </form>` : ''}
        </div>
      </div>
      ${messageHtml()}
    </div>
  `);

  loadTurnstileIfNeeded();
  renderCaptcha();

  document.getElementById('login-form').onsubmit = async (e) => {
    e.preventDefault();
    clearMessage();
    const fd = new FormData(e.target);
    try {
      await post('/api/auth/login', {
        user: fd.get('user'),
        passwd: fd.get('passwd'),
        cf_token: state.loginToken,
      });
      setMessage('Login success.', true);
      state.session = await api('/api/auth/session');
      render();
    } catch (err) {
      setMessage(err.message);
      render();
    }
  };

  document.getElementById('register-form').onsubmit = async (e) => {
    e.preventDefault();
    clearMessage();
    const fd = new FormData(e.target);
    try {
      await post('/api/auth/register', {
        user: fd.get('user'),
        email: fd.get('email'),
        passwd: fd.get('passwd'),
        cpasswd: fd.get('cpasswd'),
        cf_token: state.registerToken,
      });
      setMessage('Register success. You can login now.', true);
    } catch (err) {
      setMessage(err.message);
    }
    render();
  };

  document.getElementById('forgot-form').onsubmit = async (e) => {
    e.preventDefault();
    clearMessage();
    const fd = new FormData(e.target);
    try {
      await post('/api/auth/forgot', { email: fd.get('email') });
      setMessage('If this email exists, reset mail has been sent.', true);
    } catch (err) {
      setMessage(err.message);
    }
    render();
  };

  const verifyForm = document.getElementById('verify-form');
  if (verifyForm) {
    verifyForm.onsubmit = async (e) => {
      e.preventDefault();
      clearMessage();
      const fd = new FormData(e.target);
      try {
        await post('/api/auth/verify', { user: fd.get('user'), code: fd.get('code') });
        state.session = await api('/api/auth/session');
        setMessage('Verified and logged in.', true);
      } catch (err) {
        setMessage(err.message);
      }
      render();
    };
  }
}

function navTabs(user) {
  const tabs = ['dashboard', 'servers', 'account'];
  if (state.config.features.store) tabs.push('store');
  if (state.config.features.afk) tabs.push('afk');
  if (user.isAdmin) tabs.push('admin');

  return `<nav>${tabs.map((t) => `<button class="secondary" data-tab="${t}">${t}</button>`).join('')}<button class="danger" id="logout">Logout</button></nav>`;
}

async function dashboardView() {
  const data = await api('/api/dashboard');
  return `
    <div class="card">
      <h2>Dashboard</h2>
      <small>${data.user} | Coins: ${data.coin}</small>
      <div class="row" style="margin-top:12px">
        ${Object.entries(data.resources).map(([k, v]) => `<div class="col card"><h3>${k.toUpperCase()}</h3><p>${v.available} / ${v.total}</p></div>`).join('')}
      </div>
      <div style="height:14px"></div>
      <h3>Servers (${data.servers.length})</h3>
      <table class="table"><thead><tr><th>Name</th><th>Identifier</th><th>Status</th><th>CPU</th><th>RAM</th><th>Disk</th></tr></thead><tbody>
        ${data.servers.map((s) => `<tr><td>${s.name}</td><td>${s.identifier}</td><td>${s.status || 'active'}</td><td>${s.limits?.cpu ?? '-'}</td><td>${s.limits?.memory ?? '-'}</td><td>${s.limits?.disk ?? '-'}</td></tr>`).join('')}
      </tbody></table>
    </div>`;
}

async function serversView() {
  const data = await api('/api/servers');
  state.serverData = data;
  const nodeOptions = Object.entries(data.nodes || {}).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join('');
  return `
    <div class="card">
      <h2>Servers</h2>
      <form id="create-server" class="row" style="margin-bottom:12px">
        <div class="col"><input name="name" placeholder="Name" required /></div>
        <div class="col"><input name="cpu" type="number" min="1" placeholder="CPU" required /></div>
        <div class="col"><input name="ram" type="number" min="1" placeholder="RAM" required /></div>
        <div class="col"><input name="disk" type="number" min="1" placeholder="Disk" required /></div>
        <div class="col"><select name="node"><option value="">Auto node</option>${nodeOptions}</select></div>
        <div class="col"><select name="egg" id="egg-select">${Object.entries(data.eggs).map(([k,v])=>`<option value="${k}">${v.name}</option>`).join('')}</select></div>
        <div id="egg-variables" class="row" style="width: 100%; margin-top: 8px; flex-wrap: wrap; gap: 8px;"></div>
        <div class="col" style="width: 100%; margin-top: 8px;"><button style="width: auto;">Create</button></div>
      </form>
      <table class="table"><thead><tr><th>Name</th><th>ID</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        ${data.servers.map((s) => `<tr><td>${s.name}</td><td>${s.identifier}</td><td id="status-${s.identifier}">${s.status || 'active'}</td><td><button data-power="${s.identifier}" data-action="start">Start</button> <button data-power="${s.identifier}" data-action="stop">Stop</button> <button data-power="${s.identifier}" data-action="restart">Restart</button> <button class="secondary" data-refresh-status="${s.identifier}">Refresh</button> <button class="danger" data-power="${s.identifier}" data-action="kill">Kill</button> <button class="danger" data-delete="${s.identifier}">Delete</button></td></tr>`).join('')}
      </tbody></table>
    </div>`;
}

async function accountView() {
  const data = await api('/api/account');
  const discordRow = data.discord_link
    ? `<p>Discord: <a href="${data.discord_link}" target="_blank" rel="noopener noreferrer">Join Discord</a></p>`
    : '';
  return `
    <div class="card">
      <h2>Account</h2>
      <p>User: ${data.user}</p>
      <p>Email: ${data.email}</p>
      <p>Role: ${data.isAdmin ? 'admin' : 'user'}</p>
      ${discordRow}
      <div class="row">
        <div class="col card">
          <h3>Change Password</h3>
          <form id="change-password">
            <input name="crpasswd" type="password" placeholder="Current" required />
            <div style="height:8px"></div>
            <input name="nwpasswd" type="password" placeholder="New" required />
            <div style="height:8px"></div>
            <input name="cnwpasswd" type="password" placeholder="Confirm" required />
            <div style="height:8px"></div>
            <button>Update</button>
          </form>
        </div>
        <div class="col card">
          <h3>Panel Password</h3>
          <button id="reset-ptero">Reset and Show</button>
          <p id="ptero-pass"></p>
        </div>
      </div>
    </div>`;
}

async function storeView() {
  const data = await api('/api/store');
  return `
    <div class="card">
      <h2>Store</h2>
      <p>Coins: ${data.coin}</p>
      <form id="store-buy" class="row">
        <div class="col"><select name="item"><option value="cpu">CPU</option><option value="ram">RAM</option><option value="disk">Disk</option><option value="slot">Slot</option></select></div>
        <div class="col"><input name="amount" type="number" min="1" placeholder="Amount" required /></div>
        <div class="col"><button>Buy</button></div>
      </form>
      <pre class="card">${JSON.stringify(data.store, null, 2)}</pre>
    </div>`;
}

async function adminView() {
  const data = await api('/api/admin/users');
  return `
    <div class="card">
      <h2>Admin</h2>
      <form id="admin-add" class="row" style="margin-bottom:12px">
        <div class="col"><input name="user" placeholder="User" required /></div>
        <div class="col"><input name="cpu" type="number" placeholder="CPU" /></div>
        <div class="col"><input name="ram" type="number" placeholder="RAM" /></div>
        <div class="col"><input name="disk" type="number" placeholder="Disk" /></div>
        <div class="col"><input name="slot" type="number" placeholder="Slot" /></div>
        <div class="col"><input name="coin" type="number" placeholder="Coin" /></div>
        <div class="col"><button>Add Resources</button></div>
      </form>
      <table class="table"><thead><tr><th>User</th><th>Email</th><th>Coin</th><th>CPU</th><th>Disk</th><th>RAM</th><th>Banned</th><th>Verified</th><th></th></tr></thead><tbody>
        ${data.users.map((u)=>`<tr><td>${u[0]}</td><td>${u[6]}</td><td>${u[1]}</td><td>${u[2]}</td><td>${u[3]}</td><td>${u[4]}</td><td>${u[5]}</td><td>${u[7]}</td><td><button class="danger" data-ban="${u[0]}">Toggle Ban</button></td></tr>`).join('')}
      </tbody></table>
    </div>`;
}

function afkView() {
  return `<div class="card"><h2>AFK</h2><p>Use WebSocket endpoint <code>/afk/ws</code> from your client to receive coin updates.</p></div>`;
}

async function appView() {
  const user = state.session.user;
  let content = '';

  if (state.route === 'servers') content = await serversView();
  else if (state.route === 'account') content = await accountView();
  else if (state.route === 'store') content = await storeView();
  else if (state.route === 'admin') content = await adminView();
  else if (state.route === 'afk') content = afkView();
  else content = await dashboardView();

  shell(`
    <div class="card">
      <h1>${state.config.name}</h1>
      ${navTabs(user)}
      ${messageHtml()}
    </div>
    <div style="height:12px"></div>
    ${content}
  `);

  document.querySelectorAll('[data-tab]').forEach((el) => {
    el.onclick = () => {
      clearMessage();
      state.route = el.dataset.tab;
      render();
    };
  });

  const eggSelect = document.getElementById('egg-select');
  const eggVariables = document.getElementById('egg-variables');

  if (eggSelect && eggVariables && state.serverData?.eggs) {
    const renderEggVars = () => {
      const selectedEgg = state.serverData.eggs[eggSelect.value];
      if (!selectedEgg?.info?.environment) {
        eggVariables.innerHTML = '';
        return;
      }
      const envs = selectedEgg.info.environment;
      eggVariables.innerHTML = Object.entries(envs).map(([k, v]) => `
        <div class="col" style="min-width: 200px;">
          <label style="font-size: 0.8em; opacity: 0.8; display: block; margin-bottom: 4px;">${k}</label>
          <input name="env_${k}" value="${v}" placeholder="${k}" required style="width: 100%; box-sizing: border-box;" />
        </div>
      `).join('');
    };
    eggSelect.addEventListener('change', renderEggVars);
    renderEggVars();
  }

  const logout = document.getElementById('logout');
  if (logout) {
    logout.onclick = async () => {
      await post('/api/auth/logout', {});
      state.session = await api('/api/auth/session');
      state.route = 'dashboard';
      clearMessage();
      render();
    };
  }

  const createServer = document.getElementById('create-server');
  if (createServer) {
    createServer.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await post('/api/servers', Object.fromEntries(fd.entries()));
        setMessage('Server created.', true);
      } catch (err) {
        setMessage(err.message);
      }
      render();
    };
  }

  document.querySelectorAll('[data-delete]').forEach((el) => {
    el.onclick = async () => {
      try {
        await del(`/api/servers/${el.dataset.delete}`);
        setMessage('Server deleted.', true);
      } catch (err) {
        setMessage(err.message);
      }
      render();
    };
  });

  document.querySelectorAll('[data-power]').forEach((el) => {
    el.onclick = async () => {
      try {
        const action = el.dataset.action;
        const id = el.dataset.power;
        const res = await post(`/api/servers/${id}/power`, { action });
        const statusEl = document.getElementById(`status-${id}`);
        if (statusEl && res?.status) statusEl.textContent = res.status;
        setMessage(`Power action "${action}" sent.`, true);
      } catch (err) {
        setMessage(err.message);
      }
    };
  });

  document.querySelectorAll('[data-refresh-status]').forEach((el) => {
    el.onclick = async () => {
      try {
        const id = el.dataset.refreshStatus;
        const res = await api(`/api/servers/${id}/status`);
        const statusEl = document.getElementById(`status-${id}`);
        if (statusEl) statusEl.textContent = res.status || 'unknown';
        setMessage('Status refreshed.', true);
      } catch (err) {
        setMessage(err.message);
      }
    };
  });

  const changePassword = document.getElementById('change-password');
  if (changePassword) {
    changePassword.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await post('/api/account/password', Object.fromEntries(fd.entries()));
        setMessage('Password changed.', true);
      } catch (err) {
        setMessage(err.message);
      }
      render();
    };
  }

  const pteroBtn = document.getElementById('reset-ptero');
  if (pteroBtn) {
    pteroBtn.onclick = async () => {
      const p = document.getElementById('ptero-pass');
      try {
        const res = await post('/api/account/ptero/reset', {});
        p.textContent = `New panel password: ${res.passwd}`;
      } catch (err) {
        p.textContent = err.message;
      }
    };
  }

  const storeBuy = document.getElementById('store-buy');
  if (storeBuy) {
    storeBuy.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await post('/api/store', Object.fromEntries(fd.entries()));
        setMessage('Purchase complete.', true);
      } catch (err) {
        setMessage(err.message);
      }
      render();
    };
  }

  const adminAdd = document.getElementById('admin-add');
  if (adminAdd) {
    adminAdd.onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      try {
        await post('/api/admin/add', Object.fromEntries(fd.entries()));
        setMessage('Resources updated.', true);
      } catch (err) {
        setMessage(err.message);
      }
      render();
    };
  }

  document.querySelectorAll('[data-ban]').forEach((el) => {
    el.onclick = async () => {
      try {
        await post('/api/admin/ban', { user: el.dataset.ban });
        setMessage('Ban state updated.', true);
      } catch (err) {
        setMessage(err.message);
      }
      render();
    };
  });
}

async function render() {
  try {
    if (!state.session?.authenticated) {
      authView();
      return;
    }
    await appView();
  } catch (err) {
    shell(`<div class="card"><h2>Error</h2><p>${err.message}</p></div>`);
  }
}

boot();
