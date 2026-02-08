/**
 * Window manager — manages the embedded browser WebContentsView.
 *
 * Uses WebContentsView (Electron 33+) instead of deprecated BrowserView.
 */

const { WebContentsView } = require('electron');

// Layout constants
const SIDEBAR_WIDTH = 250;
const NAV_BAR_HEIGHT = 50;
const STATUS_BAR_HEIGHT = 40;

class WindowManager {
  constructor(baseWindow) {
    this._baseWindow = baseWindow;
    this._browserView = null;
    this._onUrlChange = null;
  }

  createBrowserView() {
    this._browserView = new WebContentsView({
      webPreferences: {
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    this._baseWindow.contentView.addChildView(this._browserView);
    this._updateBounds();

    // Listen for window resize
    this._baseWindow.on('resize', () => this._updateBounds());

    // Track URL changes
    this._browserView.webContents.on('did-navigate', (event, url) => {
      if (this._onUrlChange) this._onUrlChange(url);
    });
    this._browserView.webContents.on('did-navigate-in-page', (event, url) => {
      if (this._onUrlChange) this._onUrlChange(url);
    });

    return this._browserView;
  }

  onUrlChange(callback) {
    this._onUrlChange = callback;
  }

  _updateBounds() {
    if (!this._browserView) return;
    const [width, height] = this._baseWindow.getContentSize();
    this._browserView.setBounds({
      x: SIDEBAR_WIDTH,
      y: NAV_BAR_HEIGHT,
      width: Math.max(0, width - SIDEBAR_WIDTH),
      height: Math.max(0, height - NAV_BAR_HEIGHT - STATUS_BAR_HEIGHT),
    });
  }

  navigate(url) {
    if (this._browserView) {
      // Ensure URL has protocol
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'https://' + url;
      }
      this._browserView.webContents.loadURL(url);
    }
  }

  goBack() {
    if (this._browserView?.webContents.canGoBack()) {
      this._browserView.webContents.goBack();
    }
  }

  goForward() {
    if (this._browserView?.webContents.canGoForward()) {
      this._browserView.webContents.goForward();
    }
  }

  reload() {
    this._browserView?.webContents.reload();
  }

  getCurrentURL() {
    return this._browserView?.webContents.getURL() || '';
  }

  getWebContents() {
    return this._browserView?.webContents;
  }

  setVisible(visible) {
    if (!this._browserView) return;
    if (visible) {
      // Re-add if not already a child
      const children = this._baseWindow.contentView.children;
      if (!children.includes(this._browserView)) {
        this._baseWindow.contentView.addChildView(this._browserView);
        this._updateBounds();
      }
    } else {
      this._baseWindow.contentView.removeChildView(this._browserView);
    }
  }
}

module.exports = WindowManager;
