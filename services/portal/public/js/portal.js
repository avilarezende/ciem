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
  if (!resp.ok) {
    $('#config-modules').innerHTML = '<p class="hint config-feedback-err">Falha ao carregar módulos.</p>';
    return;
  }
  const modules = await resp.json();
  const container = $('#config-modules');
  container.innerHTML = Object.entries(modules).map(([name, cfg]) => `
    <div class="config-row">
      <div>
        <strong>${name}</strong>
        <div class="hint">${cfg.description || ''}</div>
      </div>
      <button type="button"
              class="toggle ${cfg.enabled ? 'on' : ''}"
              role="switch"
              aria-checked="${cfg.enabled}"
              data-module="${name}"
              title="Clique para ${cfg.enabled ? 'desativar' : 'ativar'}">
        <span class="toggle-knob" aria-hidden="true"></span>
      </button>
    </div>
  `).join('');

  container.querySelectorAll('.toggle[data-module]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (currentUser?.role !== 'admin') {
        showConfigFeedback('Apenas administradores podem alterar módulos.', true);
        return;
      }
      const name = btn.dataset.module;
      const next = !btn.classList.contains('on');
      toggleModule(name, next, btn);
    });
  });
}

function showConfigFeedback(message, isError = false) {
  const feedback = $('#config-feedback');
  if (!feedback) return;
  feedback.textContent = message;
  feedback.className = isError ? 'hint config-feedback-err' : 'hint config-feedback-ok';
  feedback.classList.remove('hidden');
}

async function toggleModule(name, enabled, toggleEl) {
  if (toggleEl.classList.contains('busy')) return;
  toggleEl.classList.add('busy');
  // Atualização otimista — o usuário vê o switch mudar imediatamente
  toggleEl.classList.toggle('on', enabled);
  toggleEl.setAttribute('aria-checked', String(enabled));
  toggleEl.title = `Clique para ${enabled ? 'desativar' : 'ativar'}`;

  try {
    const resp = await api(`/config/modules/${encodeURIComponent(name)}`, {
      method: 'PUT',
      body: JSON.stringify({ enabled }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const detail = typeof err.detail === 'string' ? err.detail : 'Falha ao atualizar módulo';
      throw new Error(detail);
    }
    const data = await resp.json();
    toggleEl.classList.toggle('on', data.enabled);
    toggleEl.setAttribute('aria-checked', String(data.enabled));
    toggleEl.title = `Clique para ${data.enabled ? 'desativar' : 'ativar'}`;
    showConfigFeedback(`Módulo ${name} ${data.enabled ? 'ativado' : 'desativado'}.`);
    loadModules();
  } catch (err) {
    // Reverte UI se a API falhar
    toggleEl.classList.toggle('on', !enabled);
    toggleEl.setAttribute('aria-checked', String(!enabled));
    toggleEl.title = `Clique para ${!enabled ? 'desativar' : 'ativar'}`;
    showConfigFeedback(err.message || 'Erro ao salvar configuração.', true);
  } finally {
    toggleEl.classList.remove('busy');
  }
}

async function loadGrafanaView(view = 'overview') {
  const stats = $('#grafana-stats');
  const content = $('#grafana-content');
  if (!stats || !content) return;

  const [alarmsResp, modulesResp, historyResp] = await Promise.all([
    api('/alarms/active'),
    api('/modules/status'),
    api('/history?limit=30'),
  ]);
  const alarms = await alarmsResp.json();
  const modules = await modulesResp.json();
  const history = await historyResp.json();

  const critical = alarms.filter(a => (a.severity || '').toLowerCase() === 'critical').length;
  const warning = alarms.filter(a => (a.severity || '').toLowerCase() === 'warning').length;
  const online = modules.filter(m => m.enabled && m.health?.status === 'ok').length;
  const enabled = modules.filter(m => m.enabled).length;

  stats.innerHTML = `
    <div class="stat-card danger"><div class="value">${critical}</div><div class="label">Críticos</div></div>
    <div class="stat-card warning"><div class="value">${warning}</div><div class="label">Warnings</div></div>
    <div class="stat-card"><div class="value">${alarms.length}</div><div class="label">Alarmes ativos</div></div>
    <div class="stat-card success"><div class="value">${online}/${enabled || modules.length}</div><div class="label">Módulos online</div></div>
  `;

  if (view === 'alarms') {
    content.innerHTML = alarms.length
      ? alarms.map(a => `
        <div class="data-item">
          <div>
            <span class="severity-${a.severity || 'warning'}">[${(a.severity || 'warning').toUpperCase()}]</span>
            ${a.message || a.title || 'Alarme'} — <small>${a.source_module || a.source || ''}</small>
          </div>
          <small>${a.timestamp || ''}</small>
        </div>`).join('')
      : '<p class="hint">Nenhum alarme ativo.</p>';
  } else if (view === 'modules') {
    content.innerHTML = modules.map(m => `
      <div class="data-item">
        <div>
          <strong>${m.module}</strong>
          <div class="target-meta">${m.enabled ? 'Habilitado' : 'Desabilitado'}</div>
        </div>
        <span class="${m.enabled ? (m.health?.status === 'ok' ? 'status-ok' : 'status-error') : 'status-disabled'}">
          ${m.enabled ? (m.health?.status === 'ok' ? '● Online' : '● Indisponível') : '○ Off'}
        </span>
      </div>`).join('');
  } else if (view === 'history') {
    content.innerHTML = history.length
      ? history.map(e => `
        <div class="data-item">
          <div>${e.message || e.event_type} — <small>${e.source_module || ''}</small></div>
          <small>${e.timestamp || ''}</small>
        </div>`).join('')
      : '<p class="hint">Nenhum evento no histórico.</p>';
  } else if (view === 'sessions') {
    if (currentUser?.role !== 'admin') {
      content.innerHTML = '<p class="hint">Sessões disponíveis apenas para administradores.</p>';
    } else {
      const auditResp = await api('/sessions/audit');
      const sessions = await auditResp.json();
      content.innerHTML = sessions.length
        ? sessions.map(s => `
          <div class="data-item">
            <div><strong>${s.user}</strong> → ${s.target_host}
              <div class="target-meta">${s.protocol} · ${s.started_at || ''}</div>
            </div>
          </div>`).join('')
        : '<p class="hint">Nenhuma sessão registrada.</p>';
    }
  } else {
    content.innerHTML = `
      <div class="data-item"><div><strong>Dashboard</strong> CIEM — Visão Geral NOC</div><small>ciem-overview</small></div>
      <div class="data-item"><div><strong>Dashboard</strong> Alarmes Ativos</div><small>ciem-alarms · ${alarms.length} itens</small></div>
      <div class="data-item"><div><strong>Dashboard</strong> Módulos Coletores</div><small>ciem-modules · ${modules.length} módulos</small></div>
      <div class="data-item"><div><strong>Dashboard</strong> Histórico de Eventos</div><small>ciem-history · ${history.length} eventos</small></div>
      <div class="data-item"><div><strong>Dashboard</strong> Sessões e Auditoria</div><small>ciem-sessions</small></div>
      <p class="hint">Selecione uma aba acima para detalhar. Em stack completa Docker/K8s, o Grafana provisionado fica em /grafana/.</p>
    `;
  }
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
    if (btn.dataset.panel === 'config' && currentUser?.role === 'admin') {
      loadConfig();
    }
    if (btn.dataset.panel === 'grafana') {
      const active = document.querySelector('.g-tab.active');
      loadGrafanaView(active?.dataset.gview || 'overview');
    }
    if (btn.dataset.panel === 'dashboard') {
      loadModules();
      loadAlarms();
    }
    if (btn.dataset.panel === 'alarms') loadAlarms();
    if (btn.dataset.panel === 'history') loadHistory();
  });
});

$('#btn-guacamole-full')?.addEventListener('click', openGuacamoleFull);

document.addEventListener('click', (e) => {
  if (e.target.dataset?.goto) showPanel(e.target.dataset.goto);

  const gtab = e.target.closest?.('.g-tab');
  if (gtab) {
    $$('.g-tab').forEach(t => t.classList.remove('active'));
    gtab.classList.add('active');
    loadGrafanaView(gtab.dataset.gview || 'overview');
  }
});

// Init
if (authToken && currentUser) {
  initPortal();
} else {
  showScreen('login-screen');
}
