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
  await Promise.all([loadAuthConfig(), loadModulesConfig()]);
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

function renderLocalUsers(users) {
  const list = $('#local-users-list');
  if (!list) return;
  list.innerHTML = users.length
    ? users.map((u) => `
      <div class="data-item">
        <div>
          <strong>${escapeAttr(u.username)}</strong>
          ${u.is_default_admin ? '<span class="badge-admin">admin padrão</span>' : ''}
          <div class="target-meta">${u.role} · ${u.enabled ? 'ativo' : 'desabilitado'}</div>
        </div>
        <div class="user-actions">
          <button type="button" data-action="password" data-user="${escapeAttr(u.username)}">Alterar senha</button>
          <button type="button" data-action="toggle" data-user="${escapeAttr(u.username)}" data-enabled="${u.enabled}">
            ${u.enabled ? 'Desabilitar' : 'Habilitar'}
          </button>
          <button type="button" class="danger-btn" data-action="delete" data-user="${escapeAttr(u.username)}">Excluir</button>
        </div>
      </div>`).join('')
    : '<p class="hint">Nenhum usuário local cadastrado.</p>';

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
      <label class="opt-field opt-bool">
        <input type="checkbox" name="${field.key}" ${checked}>
        <span>${field.label}</span>
      </label>`;
  }
  const inputType = field.type === 'password' ? 'password'
    : field.type === 'number' ? 'number'
    : field.type === 'url' ? 'url' : 'text';
  return `
    <label class="opt-field">
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
        <p class="hint">Preencha URL, credenciais e opções. Os valores são salvos em <code>config/modules.yaml</code>.</p>
        <div class="opt-grid">${optionsHtml}</div>
        <button type="submit" class="btn-primary btn-save-module">Salvar configuração</button>
      </form>
    </div>`;
}

function showConfigFeedback(message, isError = false) {
  const feedback = $('#config-feedback');
  if (!feedback) return;
  feedback.textContent = message;
  feedback.className = isError ? 'hint config-feedback-err' : 'hint config-feedback-ok';
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

$('#form-ldap')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    await saveLdapForm(e.target);
  } catch (err) {
    showConfigFeedback(err.message || 'Erro ao salvar LDAP.', true);
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
