/**
 * KiPartBridge — Electron main process entry point.
 */

const { app, BaseWindow, WebContentsView, ipcMain } = require('electron');
const path = require('path');
const PythonBridge = require('./python-bridge');
const DownloadInterceptor = require('./download-interceptor');
const WindowManager = require('./window-manager');

let mainWindow;
let pythonBridge;
let windowManager;
let downloadInterceptor;

const DEFAULT_URL = 'https://www.digikey.com';

function createWindow() {
  // Create the base window
  mainWindow = new BaseWindow({
    width: 1400,
    height: 900,
    title: 'KiPartBridge',
  });

  // Create the renderer view (sidebar, nav bar, status bar)
  const rendererView = new WebContentsView({
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.contentView.addChildView(rendererView);

  // Size the renderer to fill the whole window
  const updateRendererBounds = () => {
    const [width, height] = mainWindow.getContentSize();
    rendererView.setBounds({ x: 0, y: 0, width, height });
  };
  updateRendererBounds();
  mainWindow.on('resize', updateRendererBounds);

  // Load renderer HTML
  const rendererPath = path.join(__dirname, '..', 'renderer', 'index.html');
  rendererView.webContents.loadFile(rendererPath);

  // Create the embedded browser view (positioned by WindowManager)
  windowManager = new WindowManager(mainWindow);
  windowManager.createBrowserView();

  // Track URL changes and send to renderer
  windowManager.onUrlChange((url) => {
    rendererView.webContents.send('url-changed', url);
  });

  // Start Python sidecar
  pythonBridge = new PythonBridge();
  pythonBridge.start();

  // Setup download interception
  downloadInterceptor = new DownloadInterceptor(pythonBridge, rendererView);
  downloadInterceptor.setup();

  // Navigate to default URL
  windowManager.navigate(DEFAULT_URL);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ── IPC Handlers ────────────────────────────────────────────────────────────

ipcMain.handle('navigate', (event, url) => {
  windowManager.navigate(url);
});

ipcMain.handle('navigate-back', () => {
  windowManager.goBack();
});

ipcMain.handle('navigate-forward', () => {
  windowManager.goForward();
});

ipcMain.handle('reload', () => {
  windowManager.reload();
});

ipcMain.handle('get-url', () => {
  return windowManager.getCurrentURL();
});

ipcMain.handle('list-components', async (event, options) => {
  return pythonBridge.listComponents(options);
});

ipcMain.handle('search-components', async (event, query, options) => {
  return pythonBridge.searchComponents(query, options);
});

ipcMain.handle('ping-python', async () => {
  return pythonBridge.ping();
});

ipcMain.handle('set-browser-view-visible', (event, visible) => {
  windowManager.setVisible(visible);
});

// ── App lifecycle ───────────────────────────────────────────────────────────

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (pythonBridge) pythonBridge.stop();
  app.quit();
});

app.on('activate', () => {
  if (!mainWindow) createWindow();
});
