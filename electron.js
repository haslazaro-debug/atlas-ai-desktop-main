const { app, BrowserWindow } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const waitOn = require('wait-on');

// URL твоего сервера, который мы узнали ранее
const SERVER_URL = 'http://5.75.227.111:8000';

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    icon: path.join(__dirname, 'public', 'icon.png'), // Иконка (если есть в public)
  });

  // Ждем, пока запустится сервер (на всякий случай, хотя он уже в PM2),
  // и загружаем наш веб-интерфейс
  console.log(\`Waiting for server at \${SERVER_URL}...\`);
  waitOn({ resources: [SERVER_URL], delay: 1000, timeout: 20000 }, (err) => {
    if (err) {
      console.error('Server did not start in time:', err);
      // Можно показать сообщение об ошибке в окне
      win.loadURL(path.join(__dirname, '.output/public/index.html'));
    } else {
      console.log('Server is ready! Loading UI...');
      win.loadURL(SERVER_URL);
    }
  });
  
  // Для разработки можно открыть DevTools
  // win.webContents.openDevTools();
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
