/**
 * Download interceptor — captures downloads from the embedded browser
 * and routes them through the Python processing pipeline.
 */

const { session, app } = require('electron');
const path = require('path');
const fs = require('fs');

class DownloadInterceptor {
  constructor(pythonBridge, rendererView) {
    this._pythonBridge = pythonBridge;
    this._webContents = rendererView.webContents;
    this._stagingDir = path.join(app.getPath('userData'), 'staging');
    fs.mkdirSync(this._stagingDir, { recursive: true });
  }

  setup() {
    session.defaultSession.on('will-download', (event, item, webContents) => {
      const filename = item.getFilename();
      const sourceUrl = item.getURL();
      const referrerUrl = webContents.getURL();

      // Only intercept ZIP files
      if (!filename.toLowerCase().endsWith('.zip')) {
        return; // Let non-ZIP downloads proceed normally
      }

      const savePath = path.join(this._stagingDir, `${Date.now()}_${filename}`);
      item.setSavePath(savePath);

      // Notify renderer: download started
      this._send('download-started', { filename, sourceUrl });

      item.on('updated', (event, state) => {
        if (state === 'progressing' && !item.isPaused()) {
          const received = item.getReceivedBytes();
          const total = item.getTotalBytes();
          const percent = total > 0 ? Math.round((received / total) * 100) : 0;
          this._send('download-progress', { filename, percent, received, total });
        }
      });

      item.once('done', async (event, state) => {
        if (state !== 'completed') {
          this._send('download-error', { filename, error: `Download ${state}` });
          this._cleanup(savePath);
          return;
        }

        this._send('download-complete', { filename });
        this._send('processing-started', { filename });

        try {
          const result = await this._pythonBridge.processDownload(
            savePath, sourceUrl, referrerUrl
          );
          this._send('processing-complete', result);
        } catch (err) {
          this._send('processing-error', { filename, error: err.message });
        } finally {
          this._cleanup(savePath);
        }
      });
    });
  }

  _send(channel, data) {
    if (this._webContents && !this._webContents.isDestroyed()) {
      this._webContents.send(channel, data);
    }
  }

  _cleanup(filepath) {
    try {
      if (fs.existsSync(filepath)) {
        fs.unlinkSync(filepath);
      }
    } catch (e) {
      console.error('[interceptor] Cleanup failed:', e.message);
    }
  }
}

module.exports = DownloadInterceptor;
