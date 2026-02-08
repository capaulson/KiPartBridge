/**
 * Python sidecar bridge — JSON-RPC client over stdin/stdout.
 */

const { spawn } = require('child_process');
const path = require('path');
const readline = require('readline');

class PythonBridge {
  constructor() {
    this._process = null;
    this._requestId = 0;
    this._pending = new Map(); // id -> { resolve, reject, timer }
    this._rl = null;
  }

  start() {
    const fs = require('fs');
    const { app } = require('electron');
    let pythonBin, pythonArgs, envOverrides = {};

    if (app.isPackaged) {
      // Packaged: PyInstaller binary in Resources
      const sidecarDir = path.join(process.resourcesPath, 'python', 'kipartbridge-sidecar');
      pythonBin = path.join(sidecarDir, 'kipartbridge-sidecar');
      pythonArgs = ['serve'];
    } else {
      // Dev: venv Python + source
      const pythonScript = path.join(__dirname, '..', 'python', 'main.py');
      const srcPython = path.join(__dirname, '..', 'python');
      const projectRoot = path.join(__dirname, '..', '..');
      const venvPython = path.join(projectRoot, 'venv', 'bin', 'python3');
      pythonBin = fs.existsSync(venvPython) ? venvPython : 'python3';
      pythonArgs = [pythonScript, 'serve'];
      envOverrides = { PYTHONPATH: srcPython };
    }

    this._process = spawn(pythonBin, pythonArgs, {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, ...envOverrides },
    });

    this._rl = readline.createInterface({ input: this._process.stdout });
    this._rl.on('line', (line) => this._handleLine(line));

    this._process.stderr.on('data', (data) => {
      console.log('[python]', data.toString().trim());
    });

    this._process.on('exit', (code) => {
      console.log(`[python] exited with code ${code}`);
      // Reject all pending requests
      for (const [id, { reject, timer }] of this._pending) {
        clearTimeout(timer);
        reject(new Error(`Python process exited (code ${code})`));
      }
      this._pending.clear();
      // Auto-restart after a delay
      if (code !== 0 && code !== null) {
        setTimeout(() => this.start(), 2000);
      }
    });

    return this;
  }

  stop() {
    if (this._process) {
      this._process.kill();
      this._process = null;
    }
    if (this._rl) {
      this._rl.close();
      this._rl = null;
    }
  }

  _handleLine(line) {
    try {
      const response = JSON.parse(line);
      const pending = this._pending.get(response.id);
      if (!pending) return;

      clearTimeout(pending.timer);
      this._pending.delete(response.id);

      if (response.error) {
        pending.reject(new Error(response.error.message));
      } else {
        pending.resolve(response.result);
      }
    } catch (e) {
      console.error('[python] Failed to parse response:', line);
    }
  }

  _call(method, params = {}, timeoutMs = 120000) {
    return new Promise((resolve, reject) => {
      if (!this._process) {
        reject(new Error('Python process not running'));
        return;
      }

      const id = ++this._requestId;
      const timer = setTimeout(() => {
        this._pending.delete(id);
        reject(new Error(`JSON-RPC timeout for ${method}`));
      }, timeoutMs);

      this._pending.set(id, { resolve, reject, timer });

      const request = JSON.stringify({ jsonrpc: '2.0', id, method, params });
      this._process.stdin.write(request + '\n');
    });
  }

  async ping() {
    return this._call('ping');
  }

  async processDownload(filepath, sourceUrl, referrerUrl, options = {}) {
    return this._call('process_download', {
      filepath,
      source_url: sourceUrl,
      referrer_url: referrerUrl,
      library_root: options.libraryRoot,
      overwrite: options.overwrite || false,
    });
  }

  async listComponents(options = {}) {
    return this._call('list_components', {
      library_root: options.libraryRoot,
      limit: options.limit || 100,
      offset: options.offset || 0,
    });
  }

  async searchComponents(query, options = {}) {
    return this._call('search_components', {
      query,
      library_root: options.libraryRoot,
    });
  }
}

module.exports = PythonBridge;
