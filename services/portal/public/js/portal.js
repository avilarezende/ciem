/** CIEM Portal — lógica do frontend */
const API_BASE = '/api';

let authToken = localStorage.getItem('ciem_token');
let currentUser = JSON.parse(localStorage.getItem('ciem_user') || 'null');
let analysisView = 'overview';

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

const PAGE_META = {
  dashboard: { title: 'Visão geral', subtitle: 'Estado operacional e espaço para análise' },
  browser: { title: 'Navegador', subtitle: 'Grafana, consoles e URLs embutidos no portal' },
  alarms: { title: 'Alarmes', subtitle: 'Priorize critical e high antes de warning/info' },
  history: { title: 'Histórico', subtitle: 'Últimos eventos agregados dos módulos' },
  analysis: { title: 'Análise', subtitle: 'Gráficos, insights e detalhe filtrado' },
  sessions: { title: 'Sessões', subtitle: 'SSO Guacamole e auditoria de manutenção' },
  config: { title: 'Configuração', subtitle: 'Usuários, LDAP, IA e módulos coletores' },
};

const BROWSER_HOME = 'ciem://home';
const BROWSER_STORAGE_KEY = 'ciem_browser_last';
const BROWSER_RECENTS_KEY = 'ciem_browser_recents';

let browserHistory = [];
let browserIndex = -1;
let browserCurrent = BROWSER_HOME;
let browserPresetsCache = [];
let browserLoadTimer = null;

function showPanel(name) {
  $$('.panel').forEach(p => p.classList.remove('active'));
  $$('.nav-btn').forEach(b => b.classList.remove('active'));
  $(`#panel-${name}`)?.classList.add('active');
  $(`.nav-btn[data-panel="${name}"]`)?.classList.add('active');
  const meta = PAGE_META[name] || { title: name, subtitle: '' };
  if ($('#page-title')) $('#page-title').textContent = meta.title;
  if ($('#page-subtitle')) $('#page-subtitle').textContent = meta.subtitle;
  $('.workspace')?.classList.toggle('browser-focus', name === 'browser');
  if (name === 'browser') {
    refreshBrowserPresets();
    updateBrowserChrome();
  }
}

function showConfigSection(name) {
  $$('.config-nav-btn').forEach(b => b.classList.toggle('active', b.dataset.csec === name));
  $$('.config-pane').forEach(p => p.classList.toggle('active', p.dataset.csec === name));
}

function logout() {
  authToken = null;
  currentUser = null;
  localStorage.removeItem('ciem_token');
  localStorage.removeItem('ciem_user');
  try { setCalendarOpen(false); } catch (_) { /* drawer pode não existir no login */ }
  const reminder = $('#reminder-widget');
  if (reminder) reminder.hidden = true;
  $('#reminder-reopen')?.classList.add('hidden');
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

const SEV_COLORS = { critical: '#f07178', high: '#ff8f70', warning: '#e6a23c', info: '#6cb6ff' };

function countBySeverity(alarms) {
  const counts = { critical: 0, high: 0, warning: 0, info: 0 };
  for (const a of alarms) {
    const sev = String(a.severity || 'info').toLowerCase();
    if (sev in counts) counts[sev] += 1;
    else counts.info += 1;
  }
  return counts;
}

function drawBarChart(canvas, labels, values, colors) {
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 640;
  const cssH = canvas.clientHeight || 260;
  canvas.width = Math.floor(cssW * dpr);
  canvas.height = Math.floor(cssH * dpr);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  const max = Math.max(1, ...values.map(Number));
  const padL = 28, padB = 36, padT = 18, padR = 12;
  const plotW = cssW - padL - padR;
  const plotH = cssH - padT - padB;
  const n = Math.max(labels.length, 1);
  const gap = 10;
  const barW = Math.max(16, plotW / n - gap);
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.beginPath();
  ctx.moveTo(padL, cssH - padB);
  ctx.lineTo(cssW - padR, cssH - padB);
  ctx.stroke();
  labels.forEach((label, i) => {
    const v = Number(values[i]) || 0;
    const h = (v / max) * plotH;
    const x = padL + i * (plotW / n) + gap / 2;
    const y = cssH - padB - h;
    ctx.fillStyle = colors[i] || SEV_COLORS.info;
    ctx.fillRect(x, y, barW, h);
    ctx.fillStyle = '#e8eef6';
    ctx.font = '600 12px "IBM Plex Mono", monospace';
    ctx.fillText(String(v), x + 2, Math.max(padT + 10, y - 6));
    ctx.fillStyle = '#9aabbd';
    ctx.font = '500 11px "DM Sans", sans-serif';
    ctx.fillText(String(label).slice(0, 10), x, cssH - 14);
  });
}

function renderLegend(el, labels, values, colors) {
  if (!el) return;
  el.innerHTML = labels.map((l, i) => `
    <div class="legend-item">
      <span class="legend-swatch" style="background:${colors[i]}"></span>
      <span>${escapeAttr(l)}</span>
      <strong style="margin-left:auto;font-family:var(--mono)">${values[i]}</strong>
    </div>`).join('');
}

function renderKpis(container, alarms, modules) {
  if (!container) return;
  const counts = countBySeverity(alarms);
  const online = modules.filter(m => m.enabled && m.health?.status === 'ok').length;
  const enabled = modules.filter(m => m.enabled).length;
  container.innerHTML = `
    <div class="kpi danger"><div class="kpi-label">Críticos</div><div class="kpi-value">${counts.critical}</div><div class="kpi-meta">+ ${counts.high} high</div></div>
    <div class="kpi warning"><div class="kpi-label">Warnings</div><div class="kpi-value">${counts.warning}</div><div class="kpi-meta">${counts.info} info</div></div>
    <div class="kpi accent"><div class="kpi-label">Alarmes</div><div class="kpi-value">${alarms.length}</div><div class="kpi-meta">ativos agora</div></div>
    <div class="kpi success"><div class="kpi-label">Módulos</div><div class="kpi-value">${online}/${enabled || modules.length}</div><div class="kpi-meta">online / habilitados</div></div>`;
}

async function loadModules() {
  const [modResp, alarmResp, insightsResp] = await Promise.all([
    api('/modules/status'),
    api('/alarms/active'),
    api('/insights'),
  ]);
  const modules = await modResp.json();
  const alarms = await alarmResp.json();
  const insights = insightsResp.ok ? await insightsResp.json() : { enabled: false };

  renderKpis($('#kpi-row'), alarms, modules);
  const counts = countBySeverity(alarms);
  const labels = Object.keys(counts);
  const values = labels.map(k => counts[k]);
  const colors = labels.map(k => SEV_COLORS[k]);
  drawBarChart($('#severity-chart'), labels, values, colors);
  renderLegend($('#severity-legend'), labels, values, colors);

  const status = $('#insights-status');
  if (status) status.textContent = insights.enabled ? `Atualizado · ${insights.mode || 'ativo'}` : 'Desabilitado';
  const preview = $('#insights-preview');
  if (preview) {
    if (!insights.enabled) {
      preview.innerHTML = `<p class="list-empty">Insights de IA desabilitados. ${
        currentUser?.role === 'admin' ? 'Ative em Configuração → Inteligência Artificial.' : 'Peça a um administrador para ativar.'
      }</p>`;
    } else {
      const items = insights.insights || [];
      preview.innerHTML = (insights.summary ? `<div class="insight-card"><strong>Resumo</strong><p>${escapeAttr(insights.summary)}</p></div>` : '')
        + (items.slice(0, 4).map(item => `
          <div class="insight-card">
            <strong><span class="sev sev-${escapeAttr(item.severity || 'info')}">${escapeAttr((item.severity || 'info').toUpperCase())}</span>
              ${escapeAttr(item.title || 'Insight')}</strong>
            <p>${escapeAttr(item.detail || '')}</p>
          </div>`).join('') || '<p class="list-empty">Nenhum insight gerado ainda.</p>');
    }
  }

  const grid = $('#modules-grid');
  if (grid) {
    grid.innerHTML = modules.map(m => `
      <div class="module-card">
        <div class="name">${escapeAttr(m.module)}</div>
        <div class="status ${m.enabled ? (m.health?.status === 'ok' ? 'status-ok' : 'status-error') : 'status-disabled'}">
          ${m.enabled ? (m.health?.status === 'ok' ? '● Online' : '● Indisponível') : '○ Desabilitado'}
        </div>
      </div>
    `).join('');
  }
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
      <div class="list-row">
        <div>
          <span class="sev sev-${a.severity || 'warning'}">[${(a.severity || 'warning').toUpperCase()}]</span>
          ${a.message || a.title || 'Alarme'} — <small>${a.source_module}</small>
        </div>
      </div>`).join('')
    : '<p class="list-empty">Nenhum alarme ativo no momento.</p>';
}

async function loadHistory() {
  const resp = await api('/history?limit=50');
  const events = await resp.json();
  $('#history-list').innerHTML = events.length
    ? events.map(e => `
      <div class="list-row">
        <div>${e.message || e.event_type} — <small>${e.source_module}</small></div>
        <small>${e.timestamp || ''}</small>
      </div>`).join('')
    : '<p class="list-empty">Nenhum evento registrado.</p>';
}

async function loadConfig() {
  await Promise.all([loadAuthConfig(), loadAiConfig(), loadModulesConfig()]);
}

async function loadModulesConfig() {
  const resp = await api('/config/modules');
  if (!resp.ok) {
    $('#config-modules').innerHTML = '<p class="hint config-feedback-err">Falha ao carregar módulos.</p>';
    return;
  }
  const modules = await resp.json();
  const container = $('#config-modules');
  container.innerHTML = Object.entries(modules).map(([name, cfg]) => renderModuleCard(name, cfg)).join('');

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

  container.querySelectorAll('form.module-options').forEach((form) => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      saveModuleOptions(form);
    });
  });
}

const LDAP_FIELDS = [
  { key: 'enabled', label: 'Habilitar LDAP', type: 'boolean' },
  { key: 'host', label: 'Servidor (host)', type: 'text', placeholder: 'ldap.exemplo.local' },
  { key: 'port', label: 'Porta', type: 'number', placeholder: '636' },
  { key: 'use_ssl', label: 'Usar LDAPS (SSL/TLS)', type: 'boolean' },
  { key: 'server_url', label: 'URL completa (opcional)', type: 'url', placeholder: 'ldaps://ldap.exemplo.local:636' },
  { key: 'domain', label: 'Domain', type: 'text', placeholder: 'exemplo.local' },
  { key: 'base_dn', label: 'Base DN', type: 'text', placeholder: 'ou=usuarios,dc=exemplo,dc=local' },
  { key: 'uid_attribute', label: 'Atributo UID / login', type: 'text', placeholder: 'uid ou sAMAccountName' },
  { key: 'user_filter', label: 'Filtro de busca (%s = usuário)', type: 'text', placeholder: '(uid=%s)' },
  { key: 'bind_dn', label: 'Bind DN (conta de serviço)', type: 'text' },
  { key: 'bind_password', label: 'Senha do bind', type: 'password' },
  { key: 'ca_cert_path', label: 'Certificado CA / cadeia', type: 'text', placeholder: '/etc/ciem/certs/ldap-ca.crt' },
  { key: 'client_cert_path', label: 'Certificado cliente (opcional)', type: 'text' },
  { key: 'display_name_attribute', label: 'Atributo nome de exibição', type: 'text', placeholder: 'cn' },
  { key: 'default_role', label: 'Papel padrão LDAP', type: 'text', placeholder: 'observer' },
  { key: 'verify_ssl', label: 'Verificar certificado SSL', type: 'boolean' },
];

async function loadAuthConfig() {
  const resp = await api('/config/auth');
  if (!resp.ok) {
    showConfigFeedback('Falha ao carregar autenticação.', true);
    return;
  }
  const data = await resp.json();
  renderLocalUsers(data.local_users || []);
  renderLdapForm(data.ldap || {});
}

const AI_FIELDS = [
  { key: 'enabled', label: 'Habilitar Insights de IA', type: 'boolean' },
  { key: 'provider', label: 'Provedor', type: 'text', placeholder: 'openai_compatible' },
  { key: 'base_url', label: 'URL base da API', type: 'url', placeholder: 'https://api.openai.com/v1' },
  { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'sk-... ou chave do provedor' },
  { key: 'model', label: 'Modelo', type: 'text', placeholder: 'gpt-4o-mini' },
  { key: 'organization', label: 'Organização (opcional)', type: 'text' },
  { key: 'temperature', label: 'Temperatura', type: 'number', placeholder: '0.2' },
  { key: 'max_tokens', label: 'Máx. tokens', type: 'number', placeholder: '1200' },
  { key: 'refresh_interval_seconds', label: 'Intervalo de refresh (s)', type: 'number', placeholder: '300' },
  { key: 'max_alarms', label: 'Máx. alarmes no contexto', type: 'number', placeholder: '40' },
  { key: 'max_history', label: 'Máx. eventos no contexto', type: 'number', placeholder: '60' },
  { key: 'language', label: 'Idioma das respostas', type: 'text', placeholder: 'pt-BR' },
  { key: 'verify_ssl', label: 'Verificar certificado SSL', type: 'boolean' },
  { key: 'timeout_seconds', label: 'Timeout HTTP (s)', type: 'number', placeholder: '60' },
  { key: 'chat_path', label: 'Path do chat completions', type: 'text', placeholder: '/chat/completions' },
  { key: 'system_prompt', label: 'System prompt adicional', type: 'text', placeholder: 'Instruções extras (opcional)' },
];

async function loadAiConfig() {
  const resp = await api('/config/ai');
  if (!resp.ok) {
    showConfigFeedback('Falha ao carregar configuração de IA.', true);
    return;
  }
  const data = await resp.json();
  renderAiForm(data.ai || {});
}

function renderAiForm(ai) {
  const grid = $('#ai-fields');
  if (!grid) return;
  const values = { ...ai };
  // Campo mascarado: não preencher com asteriscos no password input
  if (values.api_key_set && String(values.api_key || '').startsWith('*')) {
    values.api_key = '';
  }
  grid.innerHTML = AI_FIELDS.map((field) => renderField(field, values)).join('');
  // Mostra/oculta campos conforme enabled
  const enabledCb = grid.querySelector('input[name="enabled"]');
  const syncVisibility = () => {
    const on = enabledCb?.checked;
    grid.querySelectorAll('.field').forEach((label) => {
      const input = label.querySelector('input');
      if (!input || input.name === 'enabled') return;
      label.style.opacity = on ? '1' : '0.45';
      input.disabled = !on;
    });
  };
  enabledCb?.addEventListener('change', syncVisibility);
  syncVisibility();
}

async function saveAiForm(form) {
  const payload = {};
  form.querySelectorAll('input[name]').forEach((input) => {
    if (input.disabled && input.name !== 'enabled') return;
    if (input.type === 'checkbox') payload[input.name] = input.checked;
    else if (input.type === 'number') payload[input.name] = input.value === '' ? null : Number(input.value);
    else if (input.name === 'api_key' && !input.value) return; // não sobrescrever com vazio
    else payload[input.name] = input.value;
  });
  const resp = await api('/config/ai', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha ao salvar IA');
  }
  showConfigFeedback('Configuração de IA salva em ai.yaml. Insights visíveis a todos quando habilitado.');
  loadAiConfig();
}

async function refreshAiInsights() {
  const resp = await api('/insights/refresh', { method: 'POST' });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha ao gerar insights');
  }
  const data = await resp.json();
  showConfigFeedback(`Insights gerados (${data.mode || 'ok'}). Abra Grafana → Insights IA.`);
}

function renderLocalUsers(users) {
  const list = $('#local-users-list');
  if (!list) return;
  list.innerHTML = users.length
    ? users.map((u) => `
      <div class="list-row">
        <div>
          <strong>${escapeAttr(u.username)}</strong>
          ${u.is_default_admin ? '<span class="badge-admin">admin padrão</span>' : ''}
          <div class="meta">${u.role} · ${u.enabled ? 'ativo' : 'desabilitado'}</div>
        </div>
        <div class="user-actions">
          <button type="button" data-action="password" data-user="${escapeAttr(u.username)}">Alterar senha</button>
          <button type="button" data-action="toggle" data-user="${escapeAttr(u.username)}" data-enabled="${u.enabled}">
            ${u.enabled ? 'Desabilitar' : 'Habilitar'}
          </button>
          <button type="button" class="btn-danger btn-sm" data-action="delete" data-user="${escapeAttr(u.username)}">Excluir</button>
        </div>
      </div>`).join('')
    : '<p class="list-empty">Nenhum usuário local cadastrado.</p>';

  list.querySelectorAll('button[data-action]').forEach((btn) => {
    btn.addEventListener('click', () => handleUserAction(btn));
  });
}

async function handleUserAction(btn) {
  const username = btn.dataset.user;
  const action = btn.dataset.action;
  try {
    if (action === 'password') {
      const password = prompt(`Nova senha para ${username}:`);
      if (!password) return;
      const resp = await api(`/config/auth/users/${encodeURIComponent(username)}`, {
        method: 'PUT',
        body: JSON.stringify({ password }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha ao alterar senha');
      }
      showConfigFeedback(`Senha do usuário ${username} alterada.`);
    } else if (action === 'toggle') {
      const enabled = btn.dataset.enabled !== 'true';
      const resp = await api(`/config/auth/users/${encodeURIComponent(username)}`, {
        method: 'PUT',
        body: JSON.stringify({ enabled }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha ao atualizar usuário');
      }
      showConfigFeedback(`Usuário ${username} ${enabled ? 'habilitado' : 'desabilitado'}.`);
      loadAuthConfig();
    } else if (action === 'delete') {
      if (!confirm(`Excluir usuário local "${username}"?`)) return;
      const resp = await api(`/config/auth/users/${encodeURIComponent(username)}`, { method: 'DELETE' });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha ao excluir');
      }
      showConfigFeedback(`Usuário ${username} excluído.`);
      loadAuthConfig();
    }
  } catch (err) {
    showConfigFeedback(err.message || 'Erro na operação de usuário.', true);
  }
}

function renderLdapForm(ldap) {
  const grid = $('#ldap-fields');
  if (!grid) return;
  grid.innerHTML = LDAP_FIELDS.map((field) => renderField(field, ldap)).join('');
}

async function saveLdapForm(form) {
  const payload = {};
  form.querySelectorAll('input[name]').forEach((input) => {
    if (input.type === 'checkbox') payload[input.name] = input.checked;
    else if (input.type === 'number') payload[input.name] = input.value === '' ? null : Number(input.value);
    else payload[input.name] = input.value;
  });
  const resp = await api('/config/auth/ldap', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha ao salvar LDAP');
  }
  showConfigFeedback('Configuração LDAP salva em auth.yaml.');
  loadAuthConfig();
}

/** Campos de personalização por módulo (labels em português). */
const MODULE_FIELDS = {
  zabbix: [
    { key: 'url', label: 'URL do Zabbix', type: 'url', placeholder: 'https://zabbix.exemplo.local' },
    { key: 'username', label: 'Usuário', type: 'text', placeholder: 'Admin' },
    { key: 'password', label: 'Senha', type: 'password', placeholder: '••••••••' },
    { key: 'verify_ssl', label: 'Verificar certificado SSL', type: 'boolean' },
    { key: 'problem_limit', label: 'Limite de problemas', type: 'number', placeholder: '50' },
  ],
  cacti: [
    { key: 'url', label: 'URL do Cacti', type: 'url', placeholder: 'https://cacti.exemplo.local' },
    { key: 'username', label: 'Usuário', type: 'text' },
    { key: 'password', label: 'Senha', type: 'password' },
    { key: 'verify_ssl', label: 'Verificar certificado SSL', type: 'boolean' },
  ],
  nagios: [
    { key: 'url', label: 'URL do Nagios / Nagios XI', type: 'url', placeholder: 'https://nagios.exemplo.local' },
    { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'chave da API' },
    { key: 'verify_ssl', label: 'Verificar certificado SSL', type: 'boolean' },
  ],
  topdesk: [
    { key: 'url', label: 'URL do TOPdesk', type: 'url', placeholder: 'https://topdesk.exemplo.local' },
    { key: 'username', label: 'Usuário', type: 'text' },
    { key: 'password', label: 'Senha', type: 'password' },
    { key: 'application_password', label: 'Senha de aplicação', type: 'password' },
  ],
  inventory: [
    { key: 'url', label: 'URL da API de inventário', type: 'url', placeholder: 'https://inventory.exemplo.local/api/v1/assets' },
    { key: 'api_key', label: 'API Key', type: 'password' },
    { key: 'verify_ssl', label: 'Verificar certificado SSL', type: 'boolean' },
  ],
  syslog: [
    { key: 'url', label: 'URL da API Syslog (Graylog/ELK)', type: 'url', placeholder: 'https://syslog.exemplo.local/api' },
    { key: 'api_key', label: 'API Key', type: 'password' },
    { key: 'file_path', label: 'Caminho do arquivo local', type: 'text', placeholder: '/var/log/syslog' },
    { key: 'severity_filter', label: 'Filtro de severidade (vírgula)', type: 'text', placeholder: 'warning, error, critical' },
  ],
  email_support: [
    { key: 'provider', label: 'Provedor', type: 'text', placeholder: 'imap ou microsoft_graph' },
    { key: 'host', label: 'Servidor de e-mail', type: 'text', placeholder: 'mail.exemplo.local' },
    { key: 'username', label: 'Usuário', type: 'text' },
    { key: 'password', label: 'Senha', type: 'password' },
    { key: 'folder', label: 'Pasta', type: 'text', placeholder: 'INBOX' },
    { key: 'max_messages', label: 'Máx. mensagens', type: 'number', placeholder: '100' },
  ],
};

function escapeAttr(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatOptionValue(value) {
  if (Array.isArray(value)) return value.join(', ');
  if (value === null || value === undefined) return '';
  return String(value);
}

function renderField(field, options) {
  const raw = options?.[field.key];
  const value = formatOptionValue(raw);
  const id = `opt-${field.key}`;
  if (field.type === 'boolean') {
    const checked = raw === true || raw === 'true' ? 'checked' : '';
    return `
      <label class="field field-bool">
        <input type="checkbox" name="${field.key}" ${checked}>
        <span>${field.label}</span>
      </label>`;
  }
  const inputType = field.type === 'password' ? 'password'
    : field.type === 'number' ? 'number'
    : field.type === 'url' ? 'url' : 'text';
  return `
    <label class="field">
      <span>${field.label}</span>
      <input type="${inputType}" name="${field.key}" value="${escapeAttr(value)}"
             placeholder="${escapeAttr(field.placeholder || '')}" autocomplete="off">
    </label>`;
}

function renderModuleCard(name, cfg) {
  const fields = MODULE_FIELDS[name] || Object.keys(cfg.options || {}).map((key) => ({
    key,
    label: key,
    type: /password|secret|api_key/i.test(key) ? 'password' : 'text',
  }));
  const optionsHtml = fields.map((f) => renderField(f, cfg.options || {})).join('');
  return `
    <div class="config-card" data-module-card="${name}">
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
      <form class="module-options ${cfg.enabled ? '' : 'hidden'}" data-module="${name}">
        <h4>Parâmetros de conexão</h4>
        <p class="list-empty">Preencha URL, credenciais e opções. Os valores são salvos em <code>config/modules.yaml</code>.</p>
        <div class="field-grid">${optionsHtml}</div>
        <button type="submit" class="btn-primary btn-save-module">Salvar configuração</button>
      </form>
    </div>`;
}

function showConfigFeedback(message, isError = false) {
  const feedback = $('#config-feedback');
  if (!feedback) return;
  feedback.textContent = message;
  feedback.className = `toast ${isError ? 'err' : 'ok'}`;
  feedback.classList.remove('hidden');
}

function setModuleFormVisible(name, visible) {
  const form = document.querySelector(`form.module-options[data-module="${name}"]`);
  if (!form) return;
  form.classList.toggle('hidden', !visible);
  if (visible) {
    const first = form.querySelector('input:not([type="checkbox"])');
    first?.focus();
  }
}

async function toggleModule(name, enabled, toggleEl) {
  if (toggleEl.classList.contains('busy')) return;
  toggleEl.classList.add('busy');
  toggleEl.classList.toggle('on', enabled);
  toggleEl.setAttribute('aria-checked', String(enabled));
  toggleEl.title = `Clique para ${enabled ? 'desativar' : 'ativar'}`;
  setModuleFormVisible(name, enabled);

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
    setModuleFormVisible(name, data.enabled);
    showConfigFeedback(
      data.enabled
        ? `Módulo ${name} ativado. Preencha e salve os parâmetros abaixo.`
        : `Módulo ${name} desativado.`
    );
    loadModules();
  } catch (err) {
    toggleEl.classList.toggle('on', !enabled);
    toggleEl.setAttribute('aria-checked', String(!enabled));
    toggleEl.title = `Clique para ${!enabled ? 'desativar' : 'ativar'}`;
    setModuleFormVisible(name, !enabled);
    showConfigFeedback(err.message || 'Erro ao salvar configuração.', true);
  } finally {
    toggleEl.classList.remove('busy');
  }
}

async function saveModuleOptions(form) {
  const name = form.dataset.module;
  const submitBtn = form.querySelector('.btn-save-module');
  if (submitBtn) submitBtn.disabled = true;

  const options = {};
  form.querySelectorAll('input[name]').forEach((input) => {
    if (input.type === 'checkbox') {
      options[input.name] = input.checked;
    } else {
      options[input.name] = input.value;
    }
  });

  try {
    const resp = await api(`/config/modules/${encodeURIComponent(name)}`, {
      method: 'PUT',
      body: JSON.stringify({ options }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      const detail = typeof err.detail === 'string' ? err.detail : 'Falha ao salvar opções';
      throw new Error(detail);
    }
    showConfigFeedback(`Configuração do módulo ${name} salva em modules.yaml.`);
  } catch (err) {
    showConfigFeedback(err.message || 'Erro ao salvar opções.', true);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function loadAnalysis(view = 'overview') {
  const stats = $('#analysis-kpis');
  const content = $('#analysis-content');
  if (!stats || !content) return;
  analysisView = view;
  $$('.seg-tab').forEach(t => t.classList.toggle('active', t.dataset.aview === view));

  const [alarmsResp, modulesResp, historyResp, insightsResp] = await Promise.all([
    api('/alarms/active'),
    api('/modules/status'),
    api('/history?limit=30'),
    api('/insights'),
  ]);
  const alarms = await alarmsResp.json();
  const modules = await modulesResp.json();
  const history = await historyResp.json();
  const insights = insightsResp.ok ? await insightsResp.json() : { enabled: false };

  const critical = alarms.filter(a => (a.severity || '').toLowerCase() === 'critical').length;
  const warning = alarms.filter(a => (a.severity || '').toLowerCase() === 'warning').length;
  const online = modules.filter(m => m.enabled && m.health?.status === 'ok').length;
  const enabled = modules.filter(m => m.enabled).length;

  const canvas = $('#analysis-chart');
  const caption = $('#analysis-chart-caption');
  if (view === 'insights' && caption) caption.textContent = 'Gráficos sugeridos pela IA';
  else if (view === 'alarms' && caption) caption.textContent = 'Severidade dos alarmes ativos';
  else if (view === 'modules' && caption) caption.textContent = 'Saúde dos coletores';
  else if (view === 'history' && caption) caption.textContent = 'Volume recente de eventos';
  else if (caption) caption.textContent = 'Severidade e fontes';

  if (canvas) {
    if (view === 'modules') {
      const labels = modules.map(m => m.module || m.id || '?').slice(0, 8);
      const values = modules.slice(0, 8).map(m => m.enabled && m.health?.status === 'ok' ? 1 : m.enabled ? 0.35 : 0.1);
      const colors = modules.slice(0, 8).map(m => !m.enabled ? '#6d7f93' : m.health?.status === 'ok' ? '#7dcea0' : '#f07178');
      drawBarChart(canvas, labels, values, colors);
    } else if (view === 'history') {
      const byModule = {};
      history.forEach(e => { const k = e.source_module || 'outros'; byModule[k] = (byModule[k] || 0) + 1; });
      const labels = Object.keys(byModule);
      drawBarChart(canvas, labels, Object.values(byModule), labels.map((_, i) => Object.values(SEV_COLORS)[i % 4]));
    } else if (view === 'insights' && (insights.charts || []).length) {
      const c = insights.charts[0];
      drawBarChart(canvas, c.labels || [], (c.values || []).map(Number), (c.labels || []).map((_, i) => Object.values(SEV_COLORS)[i % 4]));
    } else {
      const counts = countBySeverity(alarms);
      drawBarChart(canvas, Object.keys(counts), Object.values(counts), Object.keys(counts).map(k => SEV_COLORS[k]));
    }
  }

  stats.innerHTML = `
    <div class="kpi danger"><div class="kpi-label">Críticos</div><div class="kpi-value">${critical}</div></div>
    <div class="kpi warning"><div class="kpi-label">Warnings</div><div class="kpi-value">${warning}</div></div>
    <div class="kpi accent"><div class="kpi-label">Alarmes</div><div class="kpi-value">${alarms.length}</div></div>
    <div class="kpi success"><div class="kpi-label">Módulos</div><div class="kpi-value">${online}/${enabled || modules.length}</div></div>
  `;

  if (view === 'insights') {
    if (!insights.enabled) {
      content.innerHTML = `
        <p class="list-empty">
          Insights de IA estão <strong>desabilitados</strong>.
          ${currentUser?.role === 'admin'
            ? 'Ative em <strong>Configuração → Inteligência Artificial</strong> e preencha URL, API key e modelo.'
            : 'Peça a um administrador para ativar o provedor de IA.'}
        </p>`;
      return;
    }
    const items = insights.insights || [];
    const charts = insights.charts || [];
    content.innerHTML = `
      <div class="insight-summary data-item">
        <div>
          <strong>Resumo IA</strong>
          <div class="meta">${escapeAttr(insights.summary || '')}</div>
          <div class="meta">modo: ${escapeAttr(insights.mode || '')}
            ${insights.model ? ` · modelo: ${escapeAttr(insights.model)}` : ''}
            ${insights.generated_at ? ` · ${escapeAttr(insights.generated_at)}` : ''}
          </div>
        </div>
      </div>
      ${items.map((item) => `
        <div class="list-row">
          <div>
            <span class="sev sev-${escapeAttr(item.severity || 'info')}">[${escapeAttr((item.severity || 'info').toUpperCase())}]</span>
            <strong>${escapeAttr(item.title || 'Insight')}</strong>
            <div class="meta">${escapeAttr(item.detail || '')}</div>
            ${item.recommendation ? `<div class="meta"><em>Recomendação:</em> ${escapeAttr(item.recommendation)}</div>` : ''}
          </div>
        </div>`).join('') || '<p class="list-empty">Nenhum insight gerado ainda.</p>'}
      ${charts.length ? `
        <h3>Gráficos sugeridos</h3>
        ${charts.map((c) => `
          <div class="list-row">
            <div>
              <strong>${escapeAttr(c.title || c.id)}</strong>
              <div class="meta">${escapeAttr(c.type)} · ${(c.labels || []).map(escapeAttr).join(', ')}</div>
              <div class="meta">valores: ${(c.values || []).join(', ')}</div>
            </div>
          </div>`).join('')}
      ` : ''}
    `;
    return;
  }

  if (view === 'alarms') {
    content.innerHTML = alarms.length
      ? alarms.map(a => `
        <div class="list-row">
          <div>
            <span class="sev sev-${a.severity || 'warning'}">[${(a.severity || 'warning').toUpperCase()}]</span>
            ${a.message || a.title || 'Alarme'} — <small>${a.source_module || a.source || ''}</small>
          </div>
          <small>${a.timestamp || ''}</small>
        </div>`).join('')
      : '<p class="list-empty">Nenhum alarme ativo.</p>';
  } else if (view === 'modules') {
    content.innerHTML = modules.map(m => `
      <div class="list-row">
        <div>
          <strong>${m.module}</strong>
          <div class="meta">${m.enabled ? 'Habilitado' : 'Desabilitado'}</div>
        </div>
        <span class="${m.enabled ? (m.health?.status === 'ok' ? 'status-ok' : 'status-error') : 'status-disabled'}">
          ${m.enabled ? (m.health?.status === 'ok' ? '● Online' : '● Indisponível') : '○ Off'}
        </span>
      </div>`).join('');
  } else if (view === 'history') {
    content.innerHTML = history.length
      ? history.map(e => `
        <div class="list-row">
          <div>${e.message || e.event_type} — <small>${e.source_module || ''}</small></div>
          <small>${e.timestamp || ''}</small>
        </div>`).join('')
      : '<p class="list-empty">Nenhum evento no histórico.</p>';
  } else if (view === 'sessions') {
    if (currentUser?.role !== 'admin') {
      content.innerHTML = '<p class="list-empty">Sessões disponíveis apenas para administradores.</p>';
    } else {
      const auditResp = await api('/sessions/audit');
      const sessions = await auditResp.json();
      content.innerHTML = sessions.length
        ? sessions.map(s => `
          <div class="list-row">
            <div><strong>${s.user}</strong> → ${s.target_host}
              <div class="meta">${s.protocol} · ${s.started_at || ''}</div>
            </div>
          </div>`).join('')
        : '<p class="list-empty">Nenhuma sessão registrada.</p>';
    }
  } else {
    const insightLine = insights.enabled
      ? `<div class="list-row"><div><strong>Insights IA</strong> ${escapeAttr((insights.summary || '').slice(0, 160))}</div><small>${escapeAttr(insights.mode || 'ativo')}</small></div>`
      : `<div class="list-row"><div><strong>Insights IA</strong> desabilitados</div><small>admin ativa em Configuração</small></div>`;
    content.innerHTML = `
      <div class="list-row"><div><strong>Dashboard</strong> CIEM — Visão Geral NOC</div><small>ciem-overview</small></div>
      ${insightLine}
      <div class="list-row"><div><strong>Dashboard</strong> Alarmes Ativos</div><small>ciem-alarms · ${alarms.length} itens</small></div>
      <div class="list-row"><div><strong>Dashboard</strong> Módulos Coletores</div><small>ciem-modules · ${modules.length} módulos</small></div>
      <div class="list-row"><div><strong>Dashboard</strong> Histórico de Eventos</div><small>ciem-history · ${history.length} eventos</small></div>
      <div class="list-row"><div><strong>Dashboard</strong> Sessões e Auditoria</div><small>ciem-sessions</small></div>
      <p class="list-empty">Selecione uma aba acima para detalhar. Em stack completa Docker/K8s, o Grafana provisionado fica em /grafana/.</p>
    `;
  }
}

async function loadTargets() {
  const resp = await api('/targets');
  const targets = await resp.json();
  $('#targets-list').innerHTML = targets.length
    ? targets.map(t => `
      <div class="list-row">
        <div>
          <strong>${t.name}</strong>
          <div class="meta">${t.protocol.toUpperCase()} — ${t.hostname}:${t.port} · ${t.description || ''}</div>
        </div>
        <div class="form-actions">
          <button type="button" class="btn-secondary btn-sm" data-connect-browser="${t.id}" ${t.enabled ? '' : 'disabled'}>
            No navegador
          </button>
          <button type="button" class="btn-primary btn-sm" data-connect="${t.id}" ${t.enabled ? '' : 'disabled'}>
            ${t.enabled ? 'Nova aba ↗' : 'Desabilitado'}
          </button>
        </div>
      </div>`).join('')
    : '<p class="list-empty">Nenhum alvo configurado em config/targets.yaml</p>';
  $('#targets-list')?.querySelectorAll('[data-connect]').forEach(btn => {
    btn.addEventListener('click', () => connectTarget(btn.dataset.connect, { inBrowser: false }));
  });
  $('#targets-list')?.querySelectorAll('[data-connect-browser]').forEach(btn => {
    btn.addEventListener('click', () => connectTarget(btn.dataset.connectBrowser, { inBrowser: true }));
  });
}

async function loadAudit() {
  const resp = await api('/sessions/audit');
  const sessions = await resp.json();
  $('#audit-list').innerHTML = sessions.length
    ? sessions.map(s => `
      <div class="list-row">
        <div>
          <strong>${s.user}</strong> → ${s.target_host}
          <div class="meta">${s.protocol} · ${s.started_at || ''} · ${s.duration_seconds ? s.duration_seconds + 's' : 'em andamento'}</div>
        </div>
      </div>`).join('')
    : '<p class="list-empty">Nenhuma sessão registrada ainda.</p>';
}

function ssoOpenUrl(loginUrl) {
  if (!loginUrl) return null;
  if (/^https?:\/\//i.test(loginUrl)) return loginUrl;
  if (loginUrl.startsWith('/api/')) return loginUrl;
  if (loginUrl.startsWith('/')) return `${API_BASE}${loginUrl}`;
  return `${API_BASE}/${loginUrl}`;
}

function normalizeBrowserUrl(raw) {
  const value = String(raw || '').trim();
  if (!value || value === BROWSER_HOME || value === 'about:blank') return BROWSER_HOME;
  if (/^https?:\/\//i.test(value)) return value;
  if (value.startsWith('/')) return value;
  if (value.startsWith('ciem://')) return value;
  return `https://${value}`;
}

function displayBrowserUrl(url) {
  if (!url || url === BROWSER_HOME) return '';
  return url;
}

function isLikelyEmbeddable(url) {
  if (!url || url === BROWSER_HOME) return true;
  if (url.startsWith('/')) return true;
  try {
    const u = new URL(url, window.location.origin);
    return u.origin === window.location.origin;
  } catch {
    return false;
  }
}

function readBrowserRecents() {
  try {
    const raw = JSON.parse(localStorage.getItem(BROWSER_RECENTS_KEY) || '[]');
    return Array.isArray(raw) ? raw.filter(Boolean).slice(0, 6) : [];
  } catch {
    return [];
  }
}

function pushBrowserRecent(url) {
  if (!url || url === BROWSER_HOME) return;
  const next = [url, ...readBrowserRecents().filter(u => u !== url)].slice(0, 6);
  localStorage.setItem(BROWSER_RECENTS_KEY, JSON.stringify(next));
}

function updateBrowserChrome() {
  const back = $('#browser-back');
  const forward = $('#browser-forward');
  if (back) back.disabled = browserIndex <= 0;
  if (forward) forward.disabled = browserIndex < 0 || browserIndex >= browserHistory.length - 1;
  const input = $('#browser-url');
  if (input && document.activeElement !== input) {
    input.value = displayBrowserUrl(browserCurrent);
  }
  $$('.browser-chip').forEach(chip => {
    chip.classList.toggle('active', chip.dataset.url === browserCurrent);
  });
}

function showBrowserHome() {
  browserCurrent = BROWSER_HOME;
  $('#browser-home-view')?.classList.remove('hidden');
  $('#browser-frame')?.classList.add('hidden');
  $('#browser-blocked')?.classList.add('hidden');
  const frame = $('#browser-frame');
  if (frame) frame.removeAttribute('src');
  renderBrowserHomeCards();
  updateBrowserChrome();
}

function showBrowserBlocked(url) {
  $('#browser-home-view')?.classList.add('hidden');
  $('#browser-frame')?.classList.add('hidden');
  const blocked = $('#browser-blocked');
  if (blocked) {
    blocked.classList.remove('hidden');
    blocked.dataset.url = url || '';
  }
}

function browserNavigate(rawUrl, { push = true } = {}) {
  const url = normalizeBrowserUrl(rawUrl);
  if (url === BROWSER_HOME) {
    if (push) {
      browserHistory = browserHistory.slice(0, browserIndex + 1);
      browserHistory.push(BROWSER_HOME);
      browserIndex = browserHistory.length - 1;
    }
    showBrowserHome();
    return;
  }

  browserCurrent = url;
  if (push) {
    browserHistory = browserHistory.slice(0, browserIndex + 1);
    browserHistory.push(url);
    browserIndex = browserHistory.length - 1;
  }

  localStorage.setItem(BROWSER_STORAGE_KEY, url);
  pushBrowserRecent(url);

  $('#browser-home-view')?.classList.add('hidden');
  $('#browser-blocked')?.classList.add('hidden');
  const frame = $('#browser-frame');
  if (frame) {
    frame.classList.remove('hidden');
    frame.src = url;
  }
  updateBrowserChrome();

  if (browserLoadTimer) clearTimeout(browserLoadTimer);
  // Destinos externos costumam bloquear iframe — oferecer fallback após um tempo curto
  if (!isLikelyEmbeddable(url)) {
    browserLoadTimer = setTimeout(() => {
      if (browserCurrent === url) {
        // Mantém o iframe; só destaca o atalho externo se ainda estiver na mesma URL
        $('#browser-open-ext')?.classList.add('pulse-hint');
      }
    }, 2500);
  }
}

function browserBack() {
  if (browserIndex <= 0) return;
  browserIndex -= 1;
  const url = browserHistory[browserIndex];
  if (url === BROWSER_HOME) showBrowserHome();
  else browserNavigate(url, { push: false });
}

function browserForward() {
  if (browserIndex >= browserHistory.length - 1) return;
  browserIndex += 1;
  const url = browserHistory[browserIndex];
  if (url === BROWSER_HOME) showBrowserHome();
  else browserNavigate(url, { push: false });
}

function browserReload() {
  if (browserCurrent === BROWSER_HOME) {
    showBrowserHome();
    return;
  }
  const frame = $('#browser-frame');
  if (frame?.src) {
    frame.src = frame.src;
  } else {
    browserNavigate(browserCurrent, { push: false });
  }
}

function openBrowserExternal(url = browserCurrent) {
  const target = normalizeBrowserUrl(url);
  if (!target || target === BROWSER_HOME) {
    window.open(window.location.origin + '/', '_blank', 'noopener');
    return;
  }
  const href = target.startsWith('/') ? `${window.location.origin}${target}` : target;
  window.open(href, '_blank', 'noopener');
}

function openBrowserPanel(url) {
  showPanel('browser');
  if (url) browserNavigate(url);
  else if (browserCurrent === BROWSER_HOME) showBrowserHome();
  $('#browser-url')?.focus();
}

async function buildBrowserPresets() {
  const presets = [
    { label: 'Início', url: BROWSER_HOME, kind: 'home' },
    { label: 'Grafana', url: '/grafana/', kind: 'app' },
  ];
  if (currentUser?.role === 'admin') {
    presets.push({ label: 'Guacamole', url: '__guacamole__', kind: 'sso' });
  }
  if (currentUser?.role === 'admin') {
    try {
      const resp = await api('/config/modules');
      if (resp.ok) {
        const modules = await resp.json();
        Object.entries(modules || {}).forEach(([name, cfg]) => {
          const uiUrl = cfg?.options?.url;
          if (cfg?.enabled && uiUrl && /^https?:\/\//i.test(uiUrl)) {
            presets.push({
              label: name,
              url: uiUrl,
              kind: 'module',
            });
          }
        });
      }
    } catch {
      /* presets básicos bastam */
    }
  }
  readBrowserRecents().forEach((url) => {
    if (!presets.some(p => p.url === url)) {
      let label = url;
      try {
        label = url.startsWith('/') ? url : new URL(url).hostname;
      } catch { /* keep */ }
      presets.push({ label, url, kind: 'recent' });
    }
  });
  return presets;
}

async function refreshBrowserPresets() {
  browserPresetsCache = await buildBrowserPresets();
  const host = $('#browser-presets');
  if (!host) return;
  host.innerHTML = browserPresetsCache.map(p => `
    <button type="button" class="browser-chip" data-url="${escapeAttr(p.url)}" data-kind="${escapeAttr(p.kind || '')}">
      ${escapeAttr(p.label)}
    </button>`).join('');
  host.querySelectorAll('.browser-chip').forEach((chip) => {
    chip.addEventListener('click', () => activateBrowserPreset(chip.dataset.url, chip.dataset.kind));
  });
  renderBrowserHomeCards();
  updateBrowserChrome();
}

function renderBrowserHomeCards() {
  const host = $('#browser-home-cards');
  if (!host) return;
  const cards = browserPresetsCache.filter(p => p.kind !== 'home' && p.kind !== 'recent').slice(0, 8);
  const extras = cards.length ? cards : [
    { label: 'Grafana', url: '/grafana/', kind: 'app' },
  ];
  host.innerHTML = extras.map(p => `
    <button type="button" class="browser-home-card" data-url="${escapeAttr(p.url)}" data-kind="${escapeAttr(p.kind || '')}">
      <strong>${escapeAttr(p.label)}</strong>
      <span>${escapeAttr(p.kind === 'sso' ? 'SSO no portal' : p.url)}</span>
    </button>`).join('');
  host.querySelectorAll('.browser-home-card').forEach((card) => {
    card.addEventListener('click', () => activateBrowserPreset(card.dataset.url, card.dataset.kind));
  });
}

async function activateBrowserPreset(url, kind) {
  if (kind === 'sso' || url === '__guacamole__') {
    await openGuacamoleInBrowser();
    return;
  }
  browserNavigate(url);
}

async function fetchGuacamoleSsoUrl(targetId) {
  const body = targetId ? JSON.stringify({ target_id: targetId }) : '{}';
  const resp = await api('/sso/guacamole', { method: 'POST', body });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha no SSO');
  }
  const data = await resp.json();
  const url = ssoOpenUrl(data.login_url);
  if (!url) throw new Error('URL SSO vazia');
  return url;
}

async function openGuacamoleInBrowser(targetId) {
  try {
    const url = await fetchGuacamoleSsoUrl(targetId);
    openBrowserPanel(url);
  } catch (err) {
    alert(err.message || 'Falha no SSO Guacamole');
  }
}

async function connectTarget(targetId, { inBrowser = false } = {}) {
  try {
    const url = await fetchGuacamoleSsoUrl(targetId);
    if (inBrowser) openBrowserPanel(url);
    else window.open(url, '_blank', 'noopener');
  } catch (err) {
    alert(err.message || 'Falha no SSO');
  }
}

async function openGuacamoleFull() {
  try {
    const url = await fetchGuacamoleSsoUrl();
    window.open(url, '_blank', 'noopener');
  } catch {
    /* silencioso se Guacamole indisponível */
  }
}

function bindBrowserControls() {
  $('#browser-url-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    browserNavigate($('#browser-url')?.value || '');
  });
  $('#browser-back')?.addEventListener('click', browserBack);
  $('#browser-forward')?.addEventListener('click', browserForward);
  $('#browser-reload')?.addEventListener('click', browserReload);
  $('#browser-home')?.addEventListener('click', () => browserNavigate(BROWSER_HOME));
  $('#browser-open-ext')?.addEventListener('click', () => openBrowserExternal());
  $('#browser-blocked-open')?.addEventListener('click', () => {
    openBrowserExternal($('#browser-blocked')?.dataset.url || browserCurrent);
  });
  $('#browser-frame')?.addEventListener('load', () => {
    $('#browser-open-ext')?.classList.remove('pulse-hint');
  });
  document.addEventListener('keydown', (e) => {
    if (!$('#panel-browser')?.classList.contains('active')) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'l') {
      e.preventDefault();
      $('#browser-url')?.focus();
      $('#browser-url')?.select();
    }
  });
}

function initPortal() {
  showScreen('portal-screen');
  document.body.classList.toggle('is-admin', currentUser?.role === 'admin');
  $('#user-info').textContent = `${currentUser.username} (${currentUser.role})`;
  showPanel('dashboard');
  loadModules();
  loadAlarms();
  loadHistory();
  refreshBrowserPresets();
  initReminders();
  initCalendarDrawer();
  if (currentUser?.role === 'admin') {
    loadConfig();
    loadTargets();
    loadAudit();
  }
}

/* —— Lembretes arrastáveis —— */
const REMINDERS_KEY = 'ciem_reminders';
const REMINDER_POS_KEY = 'ciem_reminder_pos';
const REMINDER_UI_KEY = 'ciem_reminder_ui';

function loadReminders() {
  try {
    const raw = JSON.parse(localStorage.getItem(REMINDERS_KEY) || '[]');
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function saveReminders(items) {
  localStorage.setItem(REMINDERS_KEY, JSON.stringify(items.slice(0, 40)));
}

function loadReminderUi() {
  try {
    return JSON.parse(localStorage.getItem(REMINDER_UI_KEY) || '{}') || {};
  } catch {
    return {};
  }
}

function saveReminderUi(patch) {
  const next = { ...loadReminderUi(), ...patch };
  localStorage.setItem(REMINDER_UI_KEY, JSON.stringify(next));
  return next;
}

function renderReminders() {
  const list = $('#reminder-list');
  if (!list) return;
  const items = loadReminders();
  if (!items.length) {
    list.innerHTML = '<li class="reminder-empty">Nenhum lembrete. Adicione abaixo.</li>';
    return;
  }
  list.innerHTML = items.map((item) => `
    <li class="reminder-item ${item.done ? 'is-done' : ''}" data-id="${escapeAttr(item.id)}">
      <input type="checkbox" ${item.done ? 'checked' : ''} aria-label="Concluir lembrete">
      <span class="reminder-text">${escapeAttr(item.text)}</span>
      <button type="button" class="reminder-delete" title="Remover" aria-label="Remover">×</button>
    </li>
  `).join('');
}

function addReminder(text) {
  const value = String(text || '').trim();
  if (!value) return;
  const items = loadReminders();
  items.unshift({
    id: `r_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`,
    text: value.slice(0, 160),
    done: false,
    createdAt: new Date().toISOString(),
  });
  saveReminders(items);
  renderReminders();
}

function toggleReminder(id, done) {
  const items = loadReminders().map((item) => (
    item.id === id ? { ...item, done: Boolean(done) } : item
  ));
  saveReminders(items);
  renderReminders();
}

function removeReminder(id) {
  saveReminders(loadReminders().filter((item) => item.id !== id));
  renderReminders();
}

function clampReminderPosition(left, top, el) {
  const margin = 8;
  const w = el?.offsetWidth || 300;
  const h = el?.offsetHeight || 120;
  const maxL = Math.max(margin, window.innerWidth - w - margin);
  const maxT = Math.max(margin, window.innerHeight - h - margin);
  return {
    left: Math.min(Math.max(margin, left), maxL),
    top: Math.min(Math.max(margin, top), maxT),
  };
}

function applyReminderPosition(pos) {
  const widget = $('#reminder-widget');
  if (!widget || !pos) return;
  const clamped = clampReminderPosition(pos.left, pos.top, widget);
  widget.style.left = `${clamped.left}px`;
  widget.style.top = `${clamped.top}px`;
  widget.style.right = 'auto';
  widget.style.bottom = 'auto';
  localStorage.setItem(REMINDER_POS_KEY, JSON.stringify(clamped));
}

function defaultReminderPosition() {
  const widget = $('#reminder-widget');
  const w = widget?.offsetWidth || 300;
  return {
    left: Math.max(16, window.innerWidth - w - 72),
    top: Math.max(96, window.innerHeight - 360),
  };
}

function showReminderWidget() {
  const widget = $('#reminder-widget');
  const reopen = $('#reminder-reopen');
  if (!widget) return;
  widget.hidden = false;
  reopen?.classList.add('hidden');
  saveReminderUi({ hidden: false });
  const saved = (() => {
    try { return JSON.parse(localStorage.getItem(REMINDER_POS_KEY) || 'null'); } catch { return null; }
  })();
  applyReminderPosition(saved || defaultReminderPosition());
}

function hideReminderWidget() {
  const widget = $('#reminder-widget');
  const reopen = $('#reminder-reopen');
  if (widget) widget.hidden = true;
  reopen?.classList.remove('hidden');
  saveReminderUi({ hidden: true });
}

function bindReminderDrag() {
  const widget = $('#reminder-widget');
  const handle = $('#reminder-drag-handle');
  if (!widget || !handle) return;

  let dragging = false;
  let startX = 0;
  let startY = 0;
  let origL = 0;
  let origT = 0;

  const onMove = (clientX, clientY) => {
    if (!dragging) return;
    const next = clampReminderPosition(
      origL + (clientX - startX),
      origT + (clientY - startY),
      widget,
    );
    widget.style.left = `${next.left}px`;
    widget.style.top = `${next.top}px`;
  };

  const onEnd = () => {
    if (!dragging) return;
    dragging = false;
    widget.classList.remove('is-dragging');
    applyReminderPosition({
      left: parseFloat(widget.style.left) || 0,
      top: parseFloat(widget.style.top) || 0,
    });
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
  };

  const onPointerMove = (e) => onMove(e.clientX, e.clientY);
  const onPointerUp = () => onEnd();

  handle.addEventListener('pointerdown', (e) => {
    if (e.button != null && e.button !== 0) return;
    if (e.target.closest('button')) return;
    e.preventDefault();
    const rect = widget.getBoundingClientRect();
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    origL = rect.left;
    origT = rect.top;
    widget.classList.add('is-dragging');
    handle.setPointerCapture?.(e.pointerId);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
  });
}

function initReminders() {
  const widget = $('#reminder-widget');
  if (!widget) return;

  renderReminders();
  bindReminderDrag();

  const ui = loadReminderUi();
  if (ui.minimized) widget.classList.add('is-minimized');
  if (ui.hidden) hideReminderWidget();
  else showReminderWidget();

  $('#reminder-form')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const input = $('#reminder-input');
    addReminder(input?.value);
    if (input) input.value = '';
    input?.focus();
  });

  $('#reminder-list')?.addEventListener('click', (e) => {
    const row = e.target.closest('.reminder-item');
    if (!row) return;
    const id = row.dataset.id;
    if (e.target.classList.contains('reminder-delete')) {
      removeReminder(id);
      return;
    }
    if (e.target.matches('input[type="checkbox"]')) {
      toggleReminder(id, e.target.checked);
    }
  });

  $('#reminder-minimize')?.addEventListener('click', () => {
    const next = !widget.classList.contains('is-minimized');
    widget.classList.toggle('is-minimized', next);
    saveReminderUi({ minimized: next });
  });

  $('#reminder-close')?.addEventListener('click', hideReminderWidget);
  $('#reminder-reopen')?.addEventListener('click', () => {
    saveReminderUi({ minimized: false });
    widget.classList.remove('is-minimized');
    showReminderWidget();
  });

  window.addEventListener('resize', () => {
    if (widget.hidden) return;
    const left = parseFloat(widget.style.left);
    const top = parseFloat(widget.style.top);
    if (Number.isFinite(left) && Number.isFinite(top)) {
      applyReminderPosition({ left, top });
    }
  });
}

/* —— Calendário deslizante (Google / Microsoft) —— */
const CAL_GOOGLE_KEY = 'ciem_calendar_google_url';
const CAL_MS_KEY = 'ciem_calendar_ms_url';
const CAL_PROVIDER_KEY = 'ciem_calendar_provider';

function isSafeCalendarEmbedUrl(raw) {
  try {
    const u = new URL(String(raw || '').trim());
    if (u.protocol !== 'https:') return false;
    const host = u.hostname.toLowerCase();
    const allowed = [
      'calendar.google.com',
      'www.google.com',
      'outlook.office.com',
      'outlook.office365.com',
      'outlook.live.com',
      'calendars.office.com',
    ];
    return allowed.some((h) => host === h || host.endsWith(`.${h}`));
  } catch {
    return false;
  }
}

function getCalendarUrls() {
  return {
    google: localStorage.getItem(CAL_GOOGLE_KEY) || '',
    microsoft: localStorage.getItem(CAL_MS_KEY) || '',
  };
}

function setCalendarOpen(open) {
  const drawer = $('#calendar-drawer');
  const backdrop = $('#calendar-backdrop');
  const tab = $('#calendar-tab');
  if (!drawer) return;
  drawer.classList.toggle('is-open', open);
  drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
  tab?.setAttribute('aria-expanded', open ? 'true' : 'false');
  backdrop?.classList.toggle('hidden', !open);
  document.body.classList.toggle('calendar-open', open);
  if (open) {
    const provider = localStorage.getItem(CAL_PROVIDER_KEY) || 'google';
    setCalendarProvider(provider === 'setup' ? 'google' : provider);
  }
}

function setCalendarProvider(provider) {
  const mode = provider || 'google';
  localStorage.setItem(CAL_PROVIDER_KEY, mode);

  $$('.calendar-provider-tab').forEach((btn) => {
    const active = btn.dataset.calProvider === mode;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });

  const setup = $('#calendar-setup');
  const empty = $('#calendar-empty');
  const frame = $('#calendar-frame');
  const urls = getCalendarUrls();

  if (mode === 'setup') {
    setup?.classList.remove('hidden');
    empty?.classList.add('hidden');
    frame?.classList.add('hidden');
    if ($('#calendar-google-url')) $('#calendar-google-url').value = urls.google;
    if ($('#calendar-ms-url')) $('#calendar-ms-url').value = urls.microsoft;
    return;
  }

  setup?.classList.add('hidden');
  const url = mode === 'microsoft' ? urls.microsoft : urls.google;
  if (url && isSafeCalendarEmbedUrl(url)) {
    empty?.classList.add('hidden');
    if (frame) {
      frame.classList.remove('hidden');
      if (frame.getAttribute('src') !== url) frame.src = url;
    }
  } else {
    if (frame) {
      frame.classList.add('hidden');
      frame.removeAttribute('src');
    }
    empty?.classList.remove('hidden');
  }
}

function initCalendarDrawer() {
  if (!$('#calendar-drawer')) return;

  const urls = getCalendarUrls();
  if ($('#calendar-google-url')) $('#calendar-google-url').value = urls.google;
  if ($('#calendar-ms-url')) $('#calendar-ms-url').value = urls.microsoft;

  const open = () => setCalendarOpen(true);
  const close = () => setCalendarOpen(false);

  $('#calendar-tab')?.addEventListener('click', () => {
    const expanded = $('#calendar-tab')?.getAttribute('aria-expanded') === 'true';
    setCalendarOpen(!expanded);
  });
  $('#btn-open-calendar')?.addEventListener('click', open);
  $('#calendar-close')?.addEventListener('click', close);
  $('#calendar-backdrop')?.addEventListener('click', close);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.body.classList.contains('calendar-open')) {
      close();
    }
  });

  document.addEventListener('click', (e) => {
    const providerBtn = e.target.closest?.('[data-cal-provider]');
    if (providerBtn?.dataset.calProvider) {
      setCalendarProvider(providerBtn.dataset.calProvider);
    }
  });

  $('#calendar-setup')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const google = ($('#calendar-google-url')?.value || '').trim();
    const microsoft = ($('#calendar-ms-url')?.value || '').trim();
    const feedback = $('#calendar-setup-feedback');

    if ((google && !isSafeCalendarEmbedUrl(google)) || (microsoft && !isSafeCalendarEmbedUrl(microsoft))) {
      if (feedback) {
        feedback.textContent = 'Use apenas URLs https de Google Calendar ou Outlook.';
        feedback.classList.remove('hidden', 'ok');
        feedback.classList.add('err');
      }
      return;
    }

    if (google) localStorage.setItem(CAL_GOOGLE_KEY, google);
    else localStorage.removeItem(CAL_GOOGLE_KEY);
    if (microsoft) localStorage.setItem(CAL_MS_KEY, microsoft);
    else localStorage.removeItem(CAL_MS_KEY);

    if (feedback) {
      feedback.textContent = 'Agendas salvas neste navegador.';
      feedback.classList.remove('hidden', 'err');
      feedback.classList.add('ok');
    }

    const prefer = google ? 'google' : (microsoft ? 'microsoft' : 'setup');
    setCalendarProvider(prefer);
  });

  $('#calendar-clear')?.addEventListener('click', () => {
    localStorage.removeItem(CAL_GOOGLE_KEY);
    localStorage.removeItem(CAL_MS_KEY);
    if ($('#calendar-google-url')) $('#calendar-google-url').value = '';
    if ($('#calendar-ms-url')) $('#calendar-ms-url').value = '';
    const feedback = $('#calendar-setup-feedback');
    if (feedback) {
      feedback.textContent = 'URLs removidas.';
      feedback.classList.remove('hidden', 'err');
      feedback.classList.add('ok');
    }
    setCalendarProvider('setup');
  });
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
    if (btn.dataset.panel === 'analysis') {
      loadAnalysis(analysisView || 'overview');
    }
    if (btn.dataset.panel === 'dashboard') {
      loadModules();
      loadAlarms();
    }
    if (btn.dataset.panel === 'alarms') loadAlarms();
    if (btn.dataset.panel === 'history') loadHistory();
    if (btn.dataset.panel === 'browser') {
      if (browserHistory.length === 0) {
        browserHistory = [BROWSER_HOME];
        browserIndex = 0;
        showBrowserHome();
      }
    }
  });
});

$('#btn-guacamole-full')?.addEventListener('click', openGuacamoleFull);
$('#btn-guacamole-browser')?.addEventListener('click', () => openGuacamoleInBrowser());

bindBrowserControls();

$('#form-ldap')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await saveLdapForm(e.target);
  } catch (err) {
    showConfigFeedback(err.message || 'Erro ao salvar LDAP.', true);
  }
});

$('#form-ai')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await saveAiForm(e.target);
  } catch (err) {
    showConfigFeedback(err.message || 'Erro ao salvar IA.', true);
  }
});

$('#btn-ai-refresh')?.addEventListener('click', async () => {
  try {
    await refreshAiInsights();
  } catch (err) {
    showConfigFeedback(err.message || 'Erro ao gerar insights.', true);
  }
});

$('#form-create-user')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const payload = {
    username: form.username.value.trim(),
    password: form.password.value,
    role: form.role.value,
    enabled: true,
  };
  try {
    const resp = await api('/config/auth/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(typeof err.detail === 'string' ? err.detail : 'Falha ao criar usuário');
    }
    form.reset();
    showConfigFeedback(`Usuário ${payload.username} criado.`);
    loadAuthConfig();
  } catch (err) {
    showConfigFeedback(err.message || 'Erro ao criar usuário.', true);
  }
});

document.addEventListener('click', (e) => {
  const goto = e.target.closest?.('[data-goto]');
  if (goto?.dataset.goto) {
    const panel = goto.dataset.goto;
    if (panel === 'browser') {
      openBrowserPanel(goto.dataset.browserUrl || null);
    } else {
      showPanel(panel);
    }
  }

  const stab = e.target.closest?.('.seg-tab');
  if (stab) {
    loadAnalysis(stab.dataset.aview || 'overview');
  }
  const cnav = e.target.closest?.('.config-nav-btn');
  if (cnav?.dataset.csec) showConfigSection(cnav.dataset.csec);
});

// Init
if (authToken && currentUser) {
  initPortal();
} else {
  showScreen('login-screen');
}
