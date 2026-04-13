(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const d of document.querySelectorAll('link[rel="modulepreload"]'))n(d);new MutationObserver(d=>{for(const c of d)if(c.type==="childList")for(const f of c.addedNodes)f.tagName==="LINK"&&f.rel==="modulepreload"&&n(f)}).observe(document,{childList:!0,subtree:!0});function a(d){const c={};return d.integrity&&(c.integrity=d.integrity),d.referrerPolicy&&(c.referrerPolicy=d.referrerPolicy),d.crossOrigin==="use-credentials"?c.credentials="include":d.crossOrigin==="anonymous"?c.credentials="omit":c.credentials="same-origin",c}function n(d){if(d.ep)return;d.ep=!0;const c=a(d);fetch(d.href,c)}})();async function p(t,e={}){const a=await fetch(t,{credentials:"include",headers:{"Content-Type":"application/json",...e.headers||{}},...e});let n={};try{n=await a.json()}catch{n={}}if(!a.ok||n.ok===!1)throw new Error(n.error||`Request failed (${a.status})`);return n}function m(t,e){return p(t,{method:"POST",body:JSON.stringify(e)})}function x(t){return p(t,{method:"DELETE"})}const D=document.getElementById("app"),s={config:null,session:null,route:"dashboard",loginToken:"",registerToken:"",message:"",serverData:null};function o(t,e=!1){s.message={text:t,ok:e}}function g(){s.message=null}function E(){return s.message?`<p class="message ${s.message.ok?"good":""}">${s.message.text}</p>`:""}function y(t){D.innerHTML=`<div class="container">${t}</div>`}async function S(){try{s.config=await p("/api/public/config"),s.session=await p("/api/auth/session")}catch(t){y(`<div class="card"><h2>Startup error</h2><p>${t.message}</p></div>`);return}u()}function q(){if(!s.config.turnstile.enable||window.turnstile)return;const t=document.createElement("script");t.src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit",t.defer=!0,t.onload=()=>k(),document.head.appendChild(t)}function k(){if(!window.turnstile||!s.config.turnstile.enable)return;const t=document.getElementById("turnstile-login");t&&!t.dataset.rendered&&(t.dataset.rendered="1",window.turnstile.render(t,{sitekey:s.config.turnstile.site_key,callback:a=>{s.loginToken=a}}));const e=document.getElementById("turnstile-register");e&&!e.dataset.rendered&&(e.dataset.rendered="1",window.turnstile.render(e,{sitekey:s.config.turnstile.site_key,callback:a=>{s.registerToken=a}}))}function I(){y(`
    <div class="card">
      <h1>${s.config.name}</h1>
      <small>API-only backend + Vite frontend</small>
      <div class="row" style="margin-top:14px">
        <div class="col card">
          <h3>Login</h3>
          <form id="login-form">
            <input name="user" placeholder="Username" required />
            <div style="height:8px"></div>
            <input name="passwd" type="password" placeholder="Password" required />
            <div style="height:8px"></div>
            ${s.config.turnstile.enable?'<div id="turnstile-login"></div><div style="height:8px"></div>':""}
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
            ${s.config.turnstile.enable?'<div id="turnstile-register"></div><div style="height:8px"></div>':""}
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
          ${s.config.features.verifyUser?`
          <div style="height:18px"></div>
          <h3>Verify Account</h3>
          <form id="verify-form">
            <input name="user" placeholder="Username" required />
            <div style="height:8px"></div>
            <input name="code" placeholder="Verify code" required />
            <div style="height:8px"></div>
            <button>Verify</button>
          </form>`:""}
        </div>
      </div>
      ${E()}
    </div>
  `),q(),k(),document.getElementById("login-form").onsubmit=async e=>{e.preventDefault(),g();const a=new FormData(e.target);try{await m("/api/auth/login",{user:a.get("user"),passwd:a.get("passwd"),cf_token:s.loginToken}),o("Login success.",!0),s.session=await p("/api/auth/session"),u()}catch(n){o(n.message),u()}},document.getElementById("register-form").onsubmit=async e=>{e.preventDefault(),g();const a=new FormData(e.target);try{await m("/api/auth/register",{user:a.get("user"),email:a.get("email"),passwd:a.get("passwd"),cpasswd:a.get("cpasswd"),cf_token:s.registerToken}),o("Register success. You can login now.",!0)}catch(n){o(n.message)}u()},document.getElementById("forgot-form").onsubmit=async e=>{e.preventDefault(),g();const a=new FormData(e.target);try{await m("/api/auth/forgot",{email:a.get("email")}),o("If this email exists, reset mail has been sent.",!0)}catch(n){o(n.message)}u()};const t=document.getElementById("verify-form");t&&(t.onsubmit=async e=>{e.preventDefault(),g();const a=new FormData(e.target);try{await m("/api/auth/verify",{user:a.get("user"),code:a.get("code")}),s.session=await p("/api/auth/session"),o("Verified and logged in.",!0)}catch(n){o(n.message)}u()})}function B(t){const e=["dashboard","servers","account"];return s.config.features.store&&e.push("store"),s.config.features.afk&&e.push("afk"),t.isAdmin&&e.push("admin"),`<nav>${e.map(a=>`<button class="secondary" data-tab="${a}">${a}</button>`).join("")}<button class="danger" id="logout">Logout</button></nav>`}async function A(){const t=await p("/api/dashboard");return`
    <div class="card">
      <h2>Dashboard</h2>
      <small>${t.user} | Coins: ${t.coin}</small>
      <div class="row" style="margin-top:12px">
        ${Object.entries(t.resources).map(([e,a])=>`<div class="col card"><h3>${e.toUpperCase()}</h3><p>${a.available} / ${a.total}</p></div>`).join("")}
      </div>
      <div style="height:14px"></div>
      <h3>Servers (${t.servers.length})</h3>
      <table class="table"><thead><tr><th>Name</th><th>Identifier</th><th>Status</th><th>CPU</th><th>RAM</th><th>Disk</th></tr></thead><tbody>
        ${t.servers.map(e=>`<tr><td>${e.name}</td><td>${e.identifier}</td><td>${e.status||"active"}</td><td>${e.limits?.cpu??"-"}</td><td>${e.limits?.memory??"-"}</td><td>${e.limits?.disk??"-"}</td></tr>`).join("")}
      </tbody></table>
    </div>`}async function C(){const t=await p("/api/servers");return s.serverData=t,`
    <div class="card">
      <h2>Servers</h2>
      <form id="create-server" class="row" style="margin-bottom:12px">
        <div class="col"><input name="name" placeholder="Name" required /></div>
        <div class="col"><input name="cpu" type="number" min="1" placeholder="CPU" required /></div>
        <div class="col"><input name="ram" type="number" min="1" placeholder="RAM" required /></div>
        <div class="col"><input name="disk" type="number" min="1" placeholder="Disk" required /></div>
        <div class="col"><select name="node"><option value="">Auto node</option>${Object.entries(t.nodes||{}).map(([a,n])=>`<option value="${a}">${n.name}</option>`).join("")}</select></div>
        <div class="col"><select name="egg" id="egg-select">${Object.entries(t.eggs).map(([a,n])=>`<option value="${a}">${n.name}</option>`).join("")}</select></div>
        <div id="egg-variables" class="row" style="width: 100%; margin-top: 8px; flex-wrap: wrap; gap: 8px;"></div>
        <div class="col" style="width: 100%; margin-top: 8px;"><button style="width: auto;">Create</button></div>
      </form>
      <table class="table"><thead><tr><th>Name</th><th>ID</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        ${t.servers.map(a=>`<tr><td>${a.name}</td><td>${a.identifier}</td><td id="status-${a.identifier}">${a.status||"active"}</td><td><button data-power="${a.identifier}" data-action="start">Start</button> <button data-power="${a.identifier}" data-action="stop">Stop</button> <button data-power="${a.identifier}" data-action="restart">Restart</button> <button class="secondary" data-refresh-status="${a.identifier}">Refresh</button> <button class="danger" data-power="${a.identifier}" data-action="kill">Kill</button> <button class="danger" data-delete="${a.identifier}">Delete</button></td></tr>`).join("")}
      </tbody></table>
    </div>`}async function P(){const t=await p("/api/account"),e=t.discord_link?`<p>Discord: <a href="${t.discord_link}" target="_blank" rel="noopener noreferrer">Join Discord</a></p>`:"";return`
    <div class="card">
      <h2>Account</h2>
      <p>User: ${t.user}</p>
      <p>Email: ${t.email}</p>
      <p>Role: ${t.isAdmin?"admin":"user"}</p>
      ${e}
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
    </div>`}async function j(){const t=await p("/api/store");return`
    <div class="card">
      <h2>Store</h2>
      <p>Coins: ${t.coin}</p>
      <form id="store-buy" class="row">
        <div class="col"><select name="item"><option value="cpu">CPU</option><option value="ram">RAM</option><option value="disk">Disk</option><option value="slot">Slot</option></select></div>
        <div class="col"><input name="amount" type="number" min="1" placeholder="Amount" required /></div>
        <div class="col"><button>Buy</button></div>
      </form>
      <pre class="card">${JSON.stringify(t.store,null,2)}</pre>
    </div>`}async function O(){return`
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
        ${(await p("/api/admin/users")).users.map(e=>`<tr><td>${e[0]}</td><td>${e[6]}</td><td>${e[1]}</td><td>${e[2]}</td><td>${e[3]}</td><td>${e[4]}</td><td>${e[5]}</td><td>${e[7]}</td><td><button class="danger" data-ban="${e[0]}">Toggle Ban</button></td></tr>`).join("")}
      </tbody></table>
    </div>`}function V(){return'<div class="card"><h2>AFK</h2><p>Use WebSocket endpoint <code>/afk/ws</code> from your client to receive coin updates.</p></div>'}async function R(){const t=s.session.user;let e="";s.route==="servers"?e=await C():s.route==="account"?e=await P():s.route==="store"?e=await j():s.route==="admin"?e=await O():s.route==="afk"?e=V():e=await A(),y(`
    <div class="card">
      <h1>${s.config.name}</h1>
      ${B(t)}
      ${E()}
    </div>
    <div style="height:12px"></div>
    ${e}
  `),document.querySelectorAll("[data-tab]").forEach(r=>{r.onclick=()=>{g(),s.route=r.dataset.tab,u()}});const a=document.getElementById("egg-select"),n=document.getElementById("egg-variables");if(a&&n&&s.serverData?.eggs){const r=()=>{const i=s.serverData.eggs[a.value];if(!i?.info?.environment){n.innerHTML="";return}const l=i.info.environment;n.innerHTML=Object.entries(l).map(([h,v])=>`
        <div class="col" style="min-width: 200px;">
          <label style="font-size: 0.8em; opacity: 0.8; display: block; margin-bottom: 4px;">${h}</label>
          <input name="env_${h}" value="${v}" placeholder="${h}" required style="width: 100%; box-sizing: border-box;" />
        </div>
      `).join("")};a.addEventListener("change",r),r()}const d=document.getElementById("logout");d&&(d.onclick=async()=>{await m("/api/auth/logout",{}),s.session=await p("/api/auth/session"),s.route="dashboard",g(),u()});const c=document.getElementById("create-server");c&&(c.onsubmit=async r=>{r.preventDefault();const i=new FormData(r.target);try{await m("/api/servers",Object.fromEntries(i.entries())),o("Server created.",!0)}catch(l){o(l.message)}u()}),document.querySelectorAll("[data-delete]").forEach(r=>{r.onclick=async()=>{try{await x(`/api/servers/${r.dataset.delete}`),o("Server deleted.",!0)}catch(i){o(i.message)}u()}}),document.querySelectorAll("[data-power]").forEach(r=>{r.onclick=async()=>{try{const i=r.dataset.action,l=r.dataset.power,h=await m(`/api/servers/${l}/power`,{action:i}),v=document.getElementById(`status-${l}`);v&&h?.status&&(v.textContent=h.status),o(`Power action "${i}" sent.`,!0)}catch(i){o(i.message)}}}),document.querySelectorAll("[data-refresh-status]").forEach(r=>{r.onclick=async()=>{try{const i=r.dataset.refreshStatus,l=await p(`/api/servers/${i}/status`),h=document.getElementById(`status-${i}`);h&&(h.textContent=l.status||"unknown"),o("Status refreshed.",!0)}catch(i){o(i.message)}}});const f=document.getElementById("change-password");f&&(f.onsubmit=async r=>{r.preventDefault();const i=new FormData(r.target);try{await m("/api/account/password",Object.fromEntries(i.entries())),o("Password changed.",!0)}catch(l){o(l.message)}u()});const b=document.getElementById("reset-ptero");b&&(b.onclick=async()=>{const r=document.getElementById("ptero-pass");try{const i=await m("/api/account/ptero/reset",{});r.textContent=`New panel password: ${i.passwd}`}catch(i){r.textContent=i.message}});const w=document.getElementById("store-buy");w&&(w.onsubmit=async r=>{r.preventDefault();const i=new FormData(r.target);try{await m("/api/store",Object.fromEntries(i.entries())),o("Purchase complete.",!0)}catch(l){o(l.message)}u()});const $=document.getElementById("admin-add");$&&($.onsubmit=async r=>{r.preventDefault();const i=new FormData(r.target);try{await m("/api/admin/add",Object.fromEntries(i.entries())),o("Resources updated.",!0)}catch(l){o(l.message)}u()}),document.querySelectorAll("[data-ban]").forEach(r=>{r.onclick=async()=>{try{await m("/api/admin/ban",{user:r.dataset.ban}),o("Ban state updated.",!0)}catch(i){o(i.message)}u()}})}async function u(){try{if(!s.session?.authenticated){I();return}await R()}catch(t){y(`<div class="card"><h2>Error</h2><p>${t.message}</p></div>`)}}S();
