// public/preload.cjs
const { contextBridge, ipcRenderer } = require('electron');

// Expose a minimal, secure API to the renderer process
contextBridge.exposeInMainWorld('desktop', {
  // App information
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  getPlatform: () => ipcRenderer.invoke('app:platform'),
  ping: () => ipcRenderer.invoke('app:ping'),

  // System information
  isElectron: true,

  // Future APIs can be added here following the same secure pattern
  // Example: fileSystem: {
  //   readFile: (path) => ipcRenderer.invoke('fs:readFile', path),
  //   writeFile: (path, data) => ipcRenderer.invoke('fs:writeFile', path, data)
  // }
});