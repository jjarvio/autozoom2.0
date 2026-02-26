const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');

const UI_PORT = process.env.DARTS_UI_PORT || '5000';
const UI_URL = `http://127.0.0.1:${UI_PORT}`;

let backendProcess = null;
let mainWindow = null;

function getPythonCommand() {
  if (process.env.PYTHON_BIN) {
    return process.env.PYTHON_BIN;
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

function startBackend() {
  return new Promise((resolve, reject) => {
    backendProcess = spawn(
      getPythonCommand(),
      ['web_ui.py'],
      {
        cwd: path.resolve(__dirname, '..'),
        env: {
          ...process.env,
          DARTS_UI_HOST: '127.0.0.1',
          DARTS_UI_PORT: UI_PORT,
        },
        stdio: 'pipe',
      }
    );

    backendProcess.stdout.on('data', (data) => {
      process.stdout.write(`[py] ${data}`);
    });

    backendProcess.stderr.on('data', (data) => {
      process.stderr.write(`[py] ${data}`);
    });

    backendProcess.on('exit', (code) => {
      if (code !== 0) {
        console.error(`Python backend exited with code ${code}`);
      }
    });

    waitForServer(15000)
      .then(resolve)
      .catch(reject);
  });
}

function waitForServer(timeoutMs) {
  const start = Date.now();

  return new Promise((resolve, reject) => {
    const tryRequest = () => {
      const req = http.get(`${UI_URL}/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) {
          resolve();
          return;
        }
        if (Date.now() - start > timeoutMs) {
          reject(new Error('Timed out waiting for Flask backend to become healthy.'));
          return;
        }
        setTimeout(tryRequest, 300);
      });

      req.on('error', () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error('Unable to connect to Flask backend.'));
          return;
        }
        setTimeout(tryRequest, 300);
      });
    };

    tryRequest();
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 420,
    height: 820,
    title: 'Darts Control',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  await mainWindow.loadURL(UI_URL);
}

app.whenReady().then(async () => {
  try {
    await startBackend();
    await createWindow();
  } catch (error) {
    dialog.showErrorBox('Sovelluksen käynnistys epäonnistui', error.message);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
