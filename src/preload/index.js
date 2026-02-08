/**
 * Preload script — exposes a safe API to the renderer via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('kipartbridge', {
  // Navigation
  navigate: (url) => ipcRenderer.invoke('navigate', url),
  navigateBack: () => ipcRenderer.invoke('navigate-back'),
  navigateForward: () => ipcRenderer.invoke('navigate-forward'),
  reload: () => ipcRenderer.invoke('reload'),
  getURL: () => ipcRenderer.invoke('get-url'),

  // Components
  listComponents: (options) => ipcRenderer.invoke('list-components', options),
  searchComponents: (query, options) => ipcRenderer.invoke('search-components', query, options),

  // Python health
  ping: () => ipcRenderer.invoke('ping-python'),

  // Browser view visibility (hide when overlays are shown)
  setBrowserViewVisible: (visible) => ipcRenderer.invoke('set-browser-view-visible', visible),

  // Event listeners
  on: (channel, callback) => {
    const validChannels = [
      'url-changed',
      'download-started',
      'download-progress',
      'download-complete',
      'processing-started',
      'processing-complete',
      'processing-error',
      'download-error',
    ];
    if (validChannels.includes(channel)) {
      const listener = (event, ...args) => callback(...args);
      ipcRenderer.on(channel, listener);
      return () => ipcRenderer.removeListener(channel, listener);
    }
  },
});
