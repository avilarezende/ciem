/** CIEM Portal — lógica do frontend */
const API_BASE = '/api';

let authToken = localStorage.getItem('ciem_token');
let currentUser = JSON.parse(localStorage.getItem('ciem_user') || 'null');

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (resp.status === 401) { logout(); throw new Error('Não autenticado'); }
  return resp;
}

function showScreen(id) {
  $$('.screen').forEach(s => s.classList.remove('active'));
  $(`#${id}`).classList.add('active');
}

function showPanel(name) {
  $$('.panel').forEach(p => p.classList.remove('active'));
  $$('.nav-btn').forEach(b => b.classList.remove('active'));
  $(`#panel-${name}`)?.classList.add('active');
  $(`.nav-btn[data-panel="${name}"]`)?.classList.add('active');
}

function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('ciem_token');
  localStorage.removeItem('ciem_user');
  showScreen('login-screen');
}

async function login(username, password) {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) throw new Error('Credenciais inválidas');
  const data = await resp.json();
  authToken = data.token;
  currentUser = data;
  localStorage.setItem('ciem_token', authToken);
  localStorage.setItem('ciem_user', JSON.stringify(data));
  initPortal();
}

async function loadModules() {
  const resp = await api('/modules/status');
  const modules = await resp.json();
  const grid = $('#modules-grid');
  grid.innerHTML = modules.map(m => `
    <div class="module-card">
      <div class="name">${m.module}</div>
      <div class="status ${m.enabled ? (m.health?.status === 'ok' ? 'status-ok' : 'status-error') : 'status-disabled'}">
        ${m.enabled ? (m.health?.status === 'ok' ? '● Online' : '● Indisponível') : '○ Desabilitado'}
      </div>
    </div>
  `).join('');
}

async function loadAlarms() {
  const resp = await api('/alarms/active');
  const alarms = await resp.json();
  const banner = $('#alarm-banner');
  if (alarms.length > 0) {
    banner.classList.remove('hidden');
    $('#alarm-count').textContent = alarms.length;
  } else {
    banner.classList.add('hidden');
  }
  $('#alarms-list').innerHTML = alarms.length
    ? alarms.map(a => `
      <div class="data-item">
        <div>
          <span class="severity-${a.severity || 'warning'}">[${(a.severity || 'warning').toUpperCase()}]</span>
          ${a.message || a.title || 'Alarme'} — <small>${a.source_module}</small>
        </div>
      </div>`).join('')
    : '<p class="hint">Nenhum alarme ativo no momento.</p>';
}

async function loadHistory() {
  const resp = await api('/history?limit=50');
  const events = await resp.json();
  $('#history-list').innerHTML = events.length
    ? events.map(e => `
      <div class="data-item">
        <div>${e.message || e.event_type} — <small>${e.source_module}</small></div>
        <small>${e.timestamp || ''}</small>
      </div>`).join('')
    : '<p class="hint">Nenhum evento registrado.</p>';
}

async function loadConfig() {
  const resp = await api('/config/modules');
  const modules = await resp.json();
  $('#config-modules').innerHTML = Object.entries(modules).map(([name, cfg]) => `
    <div class="config-row">
      <div>
        <strong>${name}</strong>
        <div class="hint">${cfg.description || ''}</div>
      </div>
      <div class="toggle ${cfg.enabled ? 'on' : ''}" data-module="${name}" title="Altere em config/modules.yaml"></div>
    </div>
  `).join('');
}

async function loadTargets() {
  const resp = await api('/targets');
  const targets = await resp.json();
  $('#targets-list').innerHTML = targets.length
    ? targets.map(t => `
      <div class="data-item">
        <div>
          <strong>${t.name}</strong>
          <div class="target-meta">${t.protocol.toUpperCase()} — ${t.hostname}:${t.port} · ${t.description || ''}</div>
        </div>
        <button class="btn-connect" ${t.enabled ? '' : 'disabled'}
          onclick="connectTarget('${t.id}')">
          ${t.enabled ? 'Conectar' : 'Desabilitado'}
        </button>
      </div>`).join('')
    : '<p class="hint">Nenhum alvo configurado em config/targets.yaml</p>';
}

async function loadAudit() {
  const resp = await api('/sessions/audit');
  const sessions = await resp.json();
  $('#audit-list').innerHTML = sessions.length
    ? sessions.map(s => `
      <div class="data-item">
        <div>
          <strong>${s.user}</strong> → ${s.target_host}
          <div class="target-meta">${s.protocol} · ${s.started_at || ''} · ${s.duration_seconds ? s.duration_seconds + 's' : 'em andamento'}</div>
        </div>
      </div>`).join('')
    : '<p class="hint">Nenhuma sessão registrada ainda.</p>';
}

async function connectTarget(targetId) {
  const resp = await api('/sso/guacamole', {
    method: 'POST',
    body: JSON.stringify({ target_id: targetId }),
  });
  const data = await resp.json();
  window.open(`/api${data.login_url}`, '_blank', 'noopener');
}
window.connectTarget = connectTarget;

async function openGuacamoleFull() {
  const resp = await api('/sso/guacamole', { method: 'POST', body: '{}' });
  const data = await resp.json();
  window.open(`/api${data.login_url}`, '_blank', 'noopener');
}

function initPortal() {
  showScreen('portal-screen');
  document.body.classList.toggle('is-admin', currentUser?.role === 'admin');
  $('#user-info').textContent = `${currentUser.username} (${currentUser.role})`;
  showPanel('dashboard');
  loadModules();
  loadAlarms();
  loadHistory();
  if (currentUser?.role === 'admin') {
    loadConfig();
    loadTargets();
    loadAudit();
  }
}

// Event listeners
$('#login-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const err = $('#login-error');
  err.classList.add('hidden');
  try {
    await login($('#username').value, $('#password').value);
  } catch {
    err.textContent = 'Usuário ou senha inválidos.';
    err.classList.remove('hidden');
  }
});

$('#logout-btn')?.addEventListener('click', logout);

$$('.nav-btn[data-panel]').forEach(btn => {
  btn.addEventListener('click', () => {
    showPanel(btn.dataset.panel);
    if (btn.dataset.panel === 'sessions' && currentUser?.role === 'admin') {
      loadTargets();
      loadAudit();
    }
  });
});

$('#btn-guacamole-full')?.addEventListener('click', openGuacamoleFull);

document.addEventListener('click', (e) => {
  if (e.target.dataset?.goto) showPanel(e.target.dataset.goto);
});

// Init
if (authToken && currentUser) {
  initPortal();
} else {
  showScreen('login-screen');
}
