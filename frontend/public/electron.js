// public/electron.js
import { app, BrowserWindow, ipcMain, session } from 'electron';
import pkg from 'electron-updater';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
const { autoUpdater } = pkg;

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const isDev = !!process.env.ELECTRON_START_URL;

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: join(__dirname, 'preload.cjs'),
      contextIsolation: true,     // recommended security
      sandbox: true,              // sandboxed renderer
      nodeIntegration: false,     // no Node in renderer
      webSecurity: true           // ensure web security is enabled
    },
    icon: join(__dirname, 'icon.png'),
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    show: false // Don't show until ready
  });

  // Show window when ready to prevent visual flash
  win.once('ready-to-show', () => {
    win.show();
    console.log('🚀 Desktop app is ready!');
    console.log('✅ Web-UI Agent Dashboard launched successfully');
    if (isDev) {
      console.log(`🔗 Connected to dev server: ${process.env.ELECTRON_START_URL}`);
      console.log('🔧 Development tools are available');
    }
  });

  if (isDev) {
    win.loadURL(process.env.ELECTRON_START_URL);
    win.webContents.openDevTools({ mode: 'detach' });
  } else {
    win.loadFile(join(__dirname, '../dist/index.html'));
  }

  return win;
}

// Strict permission handler for security
app.whenReady().then(() => {
  console.log('🔧 Initializing Electron application...');

  // Set strict permissions for any remote content
  session.defaultSession.setPermissionRequestHandler((_webContents, permission, callback) => {
    // Deny all permissions by default for security
    console.log(`Permission request for: ${permission}`);
    callback(false);
  });

  // Configure CSP for additional security
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self'; " +
          "script-src 'self' 'unsafe-inline'; " +
          "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; " +
          "img-src 'self' data: blob:; " +
          "connect-src 'self' http://localhost:* ws://localhost:* wss://localhost:* http://127.0.0.1:* ws://127.0.0.1:* wss://127.0.0.1:*; " +
          "font-src 'self' data:;"
        ]
      }
    });
  });

  console.log('📱 Creating desktop window...');
  createWindow();

  // Auto-updater in production
  if (!isDev) {
    autoUpdater.checkForUpdatesAndNotify();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Secure IPC handlers
ipcMain.handle('app:getVersion', () => {
  return app.getVersion();
});

ipcMain.handle('app:platform', () => {
  return process.platform;
});

ipcMain.handle('app:ping', () => {
  return 'pong from native';
});

// Auto-updater events
autoUpdater.on('checking-for-update', () => {
  console.log('Checking for update...');
});

autoUpdater.on('update-available', (info) => {
  console.log('Update available.');
});

autoUpdater.on('update-not-available', (info) => {
  console.log('Update not available.');
});

autoUpdater.on('error', (err) => {
  console.log('Error in auto-updater. ' + err);
});

autoUpdater.on('download-progress', (progressObj) => {
  let log_message = "Download speed: " + progressObj.bytesPerSecond;
  log_message = log_message + ' - Downloaded ' + progressObj.percent + '%';
  log_message = log_message + ' (' + progressObj.transferred + "/" + progressObj.total + ')';
  console.log(log_message);
});

autoUpdater.on('update-downloaded', (info) => {
  console.log('Update downloaded');
  autoUpdater.quitAndInstall();
});