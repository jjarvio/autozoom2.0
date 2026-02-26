const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const UI_PORT = process.env.DARTS_UI_PORT || '5000';
const UI_URL = `http://127.0.0.1:${UI_PORT}`;

let backendProcess = null;
let mainWindow = null;

function normalizeBin(bin) {
  if (!bin) {
    return null;
  }
  const trimmed = String(bin).trim();
  if (!trimmed) {
    return null;
  }
  // allow values like "C:\\path\\python.exe"
  return trimmed.replace(/^"|"$/g, '');
}

function getPythonCandidates(projectRoot) {
  const envBin = normalizeBin(process.env.PYTHON_BIN);
  const candidates = [];

  if (envBin) {
    candidates.push(envBin);
  }

  if (process.platform === 'win32') {
    candidates.push(path.join(projectRoot, 'venv', 'Scripts', 'python.exe'));
    candidates.push('python');
    candidates.push('py');
  } else {
    candidates.push(path.join(projectRoot, 'venv', 'bin', 'python3'));
    candidates.push(path.join(projectRoot, 'venv', 'bin', 'python'));
    candidates.push('python3');
    candidates.push('python');
  }

  return candidates;
}

function resolvePythonCommand(projectRoot) {
  const candidates = getPythonCandidates(projectRoot);

  for (const candidate of candidates) {
    if (path.isAbsolute(candidate)) {
      if (fs.existsSync(candidate)) {
        return { command: candidate, argsPrefix: [] };
      }
      continue;
    }

    // command from PATH
    if (candidate === 'py') {
      return { command: 'py', argsPrefix: ['-3'] };
    }
    return { command: candidate, argsPrefix: [] };
  }

  return null;
}

function startBackend() {
  return new Promise((resolve, reject) => {
    const projectRoot = path.resolve(__dirname, '..');
    const python = resolvePythonCommand(projectRoot);

    if (!python) {
      reject(new Error('Python-tulkkia ei löytynyt. Asenna Python tai aseta PYTHON_BIN.'));
      return;
    }

    const backendArgs = [...python.argsPrefix, 'web_ui.py'];

    backendProcess = spawn(python.command, backendArgs, {
      cwd: projectRoot,
      env: {
        ...process.env,
        DARTS_UI_HOST: '127.0.0.1',
        DARTS_UI_PORT: UI_PORT,
      },
      stdio: 'pipe',
    });

    backendProcess.stdout.on('data', (data) => {
      process.stdout.write(`[py] ${data}`);
    });

    backendProcess.stderr.on('data', (data) => {
      process.stderr.write(`[py] ${data}`);
    });

    backendProcess.on('error', (error) => {
      reject(new Error(`Python-backendin käynnistys epäonnistui (${python.command}): ${error.message}`));
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
