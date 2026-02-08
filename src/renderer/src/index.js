/**
 * KiPartBridge renderer — full UI with sidebar, nav, status, settings, library browser.
 */

const QUICK_LINKS = [
  { name: 'DigiKey', url: 'https://www.digikey.com', icon: 'DK', cls: 'dk' },
  { name: 'Mouser', url: 'https://www.mouser.com', icon: 'MO', cls: 'mo' },
  { name: 'LCSC', url: 'https://www.lcsc.com', icon: 'LC', cls: 'lc' },
  { name: 'SnapEDA', url: 'https://www.snapeda.com', icon: 'SE', cls: 'sn' },
  { name: 'CSE', url: 'https://componentsearchengine.com', icon: 'CS', cls: 'cs' },
  { name: 'Ultra Librarian', url: 'https://www.ultralibrarian.com', icon: 'UL', cls: 'ul' },
];

// ── Build DOM ───────────────────────────────────────────────────────────────

const root = document.getElementById('root');
root.innerHTML = `
  <div id="app">
    <!-- Sidebar -->
    <div id="sidebar">
      <div id="sidebar-header">
        <h2><span class="logo">KB</span> KiPartBridge</h2>
      </div>
      <div id="sidebar-content">
        <div class="sidebar-section">
          <h3>Suppliers</h3>
          <ul id="links-list"></ul>
        </div>
        <div class="sidebar-section">
          <h3>Recent Imports</h3>
          <ul id="imports-list">
            <li class="empty">No imports yet</li>
          </ul>
        </div>
      </div>
      <div id="sidebar-footer">
        <button id="btn-library">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          Library Browser
        </button>
      </div>
    </div>

    <!-- Nav Bar -->
    <div id="nav-bar">
      <button class="nav-btn" id="btn-back" title="Back">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <button class="nav-btn" id="btn-forward" title="Forward">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
      <button class="nav-btn" id="btn-reload" title="Reload">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
      </button>
      <input id="url-input" type="text" placeholder="Enter URL or search..." spellcheck="false" />
      <button class="nav-btn" id="btn-settings" title="Settings">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      </button>
    </div>

    <!-- Status Bar -->
    <div id="status-bar">
      <span id="status-dot" class="ready"></span>
      <span id="status-text">Ready</span>
    </div>
  </div>

  <!-- Settings Overlay -->
  <div id="settings-overlay">
    <div id="settings-panel">
      <h2>Settings</h2>
      <div class="setting-group">
        <label>Library Root Path</label>
        <input type="text" id="setting-lib-root" value="~/.kicad_libs/kipartbridge" />
      </div>
      <div class="setting-group">
        <label>Library Name</label>
        <input type="text" id="setting-lib-name" value="kipartbridge" />
      </div>
      <div class="setting-group">
        <label>3D Model Environment Variable</label>
        <input type="text" id="setting-3d-var" value="KIPARTBRIDGE_3DMODELS" />
      </div>
      <div class="setting-group">
        <label>Browser Homepage</label>
        <input type="text" id="setting-homepage" value="https://www.digikey.com" />
      </div>
      <div class="settings-actions">
        <button class="btn-secondary" id="settings-cancel">Cancel</button>
        <button class="btn-primary" id="settings-save">Save</button>
      </div>
    </div>
  </div>

  <!-- Library Browser Overlay -->
  <div id="library-overlay">
    <div id="library-panel">
      <div id="library-header">
        <h2>Imported Components</h2>
        <input type="text" id="library-search" placeholder="Search MPN..." />
        <button id="library-close">&times;</button>
      </div>
      <div id="library-table-wrap">
        <table id="library-table">
          <thead>
            <tr>
              <th>MPN</th>
              <th>Manufacturer</th>
              <th>Provider</th>
              <th>3D</th>
              <th>Imported</th>
            </tr>
          </thead>
          <tbody id="library-tbody"></tbody>
        </table>
        <div id="library-empty">No components imported yet</div>
      </div>
    </div>
  </div>
`;

// ── Quick Links ─────────────────────────────────────────────────────────────

const linksList = document.getElementById('links-list');
for (const link of QUICK_LINKS) {
  const li = document.createElement('li');
  li.innerHTML = `<span class="link-icon ${link.cls}">${link.icon}</span> ${link.name}`;
  li.addEventListener('click', () => window.kipartbridge.navigate(link.url));
  linksList.appendChild(li);
}

// ── Navigation ──────────────────────────────────────────────────────────────

document.getElementById('btn-back').addEventListener('click', () => window.kipartbridge.navigateBack());
document.getElementById('btn-forward').addEventListener('click', () => window.kipartbridge.navigateForward());
document.getElementById('btn-reload').addEventListener('click', () => window.kipartbridge.reload());

const urlInput = document.getElementById('url-input');
urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') window.kipartbridge.navigate(urlInput.value);
});

window.kipartbridge.on('url-changed', (url) => { urlInput.value = url; });

// ── Status Bar ──────────────────────────────────────────────────────────────

const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

function setStatus(state, text) {
  statusDot.className = state;
  statusText.textContent = text;
}

// ── Recent Imports ──────────────────────────────────────────────────────────

const importsList = document.getElementById('imports-list');

function addImport(mpn, status) {
  const empty = importsList.querySelector('.empty');
  if (empty) empty.remove();

  const li = document.createElement('li');
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  li.innerHTML = `
    <div class="import-item">
      <span class="import-status ${status}"></span>
      <span class="import-mpn">${mpn}</span>
      <span class="import-time">${time}</span>
    </div>
  `;
  importsList.prepend(li);
}

// ── Download & Processing Events ────────────────────────────────────────────

setStatus('ready', 'Ready');

window.kipartbridge.on('download-started', (d) => setStatus('downloading', `Downloading ${d.filename}...`));
window.kipartbridge.on('download-progress', (d) => setStatus('downloading', `Downloading... ${d.percent}%`));
window.kipartbridge.on('download-complete', (d) => setStatus('processing', `Processing ${d.filename}...`));
window.kipartbridge.on('processing-started', (d) => setStatus('processing', `Processing ${d.filename}...`));

window.kipartbridge.on('processing-complete', (r) => {
  if (r.status === 'success') {
    setStatus('success', `Imported ${r.mpn}`);
    addImport(r.mpn, 'success');
  } else if (r.status === 'partial') {
    setStatus('success', `Partially imported ${r.mpn}`);
    addImport(r.mpn, 'partial');
  } else {
    setStatus('error', `Error: ${r.error || 'unknown'}`);
    addImport(r.mpn || 'unknown', 'error');
  }
  setTimeout(() => setStatus('ready', 'Ready'), 5000);
});

window.kipartbridge.on('processing-error', (d) => {
  setStatus('error', `Error: ${d.error}`);
  addImport(d.filename, 'error');
  setTimeout(() => setStatus('ready', 'Ready'), 5000);
});

window.kipartbridge.on('download-error', (d) => {
  setStatus('error', `Download failed: ${d.error}`);
  setTimeout(() => setStatus('ready', 'Ready'), 5000);
});

// ── Overlay helpers (hide browser view so overlays are visible) ──────────────

function showOverlay(overlay) {
  overlay.classList.add('visible');
  window.kipartbridge.setBrowserViewVisible(false);
}

function hideOverlay(overlay) {
  overlay.classList.remove('visible');
  // Only restore browser view if no overlays are open
  const anyOpen = document.querySelector('#settings-overlay.visible, #library-overlay.visible');
  if (!anyOpen) {
    window.kipartbridge.setBrowserViewVisible(true);
  }
}

// ── Settings Panel ──────────────────────────────────────────────────────────

const settingsOverlay = document.getElementById('settings-overlay');

document.getElementById('btn-settings').addEventListener('click', () => {
  showOverlay(settingsOverlay);
});

document.getElementById('settings-cancel').addEventListener('click', () => {
  hideOverlay(settingsOverlay);
});

document.getElementById('settings-save').addEventListener('click', () => {
  hideOverlay(settingsOverlay);
});

settingsOverlay.addEventListener('click', (e) => {
  if (e.target === settingsOverlay) hideOverlay(settingsOverlay);
});

// ── Library Browser ─────────────────────────────────────────────────────────

const libraryOverlay = document.getElementById('library-overlay');
const libraryTbody = document.getElementById('library-tbody');
const libraryEmpty = document.getElementById('library-empty');
const librarySearch = document.getElementById('library-search');

document.getElementById('btn-library').addEventListener('click', async () => {
  showOverlay(libraryOverlay);
  await loadLibrary();
});

document.getElementById('library-close').addEventListener('click', () => {
  hideOverlay(libraryOverlay);
});

libraryOverlay.addEventListener('click', (e) => {
  if (e.target === libraryOverlay) hideOverlay(libraryOverlay);
});

let searchTimeout;
librarySearch.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadLibrary(librarySearch.value), 300);
});

async function loadLibrary(query) {
  try {
    let components;
    if (query && query.trim()) {
      components = await window.kipartbridge.searchComponents(query.trim());
    } else {
      components = await window.kipartbridge.listComponents();
    }

    libraryTbody.innerHTML = '';
    if (!components || components.length === 0) {
      libraryEmpty.style.display = 'block';
      return;
    }
    libraryEmpty.style.display = 'none';

    for (const comp of components) {
      const tr = document.createElement('tr');
      const date = comp.updated_at ? new Date(comp.updated_at).toLocaleDateString() : '-';
      const has3d = comp.has_3d_model ? '\u2713' : '-';
      tr.innerHTML = `
        <td style="color:var(--text-primary);font-weight:500">${comp.mpn || '-'}</td>
        <td>${comp.manufacturer || '-'}</td>
        <td>${comp.source_provider || '-'}</td>
        <td style="text-align:center">${has3d}</td>
        <td>${date}</td>
      `;
      libraryTbody.appendChild(tr);
    }
  } catch (err) {
    console.error('Failed to load library:', err);
    libraryEmpty.textContent = 'Failed to load components';
    libraryEmpty.style.display = 'block';
  }
}
