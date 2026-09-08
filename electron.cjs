const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200, // Сделали нормальную ширину под ПК
    height: 800,  // И нормальную высоту
    frame: false,         
    transparent: true,     
    backgroundColor: '#00000000', 
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Проверяем: если мы запускаем локально в разработке, можно грузить с локалхоста, 
  // а при продакшене — скомпилированный index.html
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

  if (isDev) {
    // Если проект запущен локально, открываем Vite-сервер (порт может отличаться, обычно 3000 или 5173)
    mainWindow.loadURL('http://localhost:3000').catch(() => {
      // Если сервер не запущен, грузим файл из дистрибутива
      mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
    });
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist/index.html'));
  }
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
