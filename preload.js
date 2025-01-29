const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  sendMessage: (message) => ipcRenderer.send('send-message', message),
  onReceiveMessage: (callback) => ipcRenderer.on('receive-message', (event, message) => callback(message)),
  openDirectoryDialog: () => ipcRenderer.invoke('open-directory-dialog')
});