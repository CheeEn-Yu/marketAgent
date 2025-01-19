import { app, BrowserWindow, ipcMain, Menu } from 'electron';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execFile } from 'child_process';
import { promises as fs } from 'fs';
import { tmpdir } from 'os';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function callPythonReverseString(inputString) {
    const scriptPath = join(app.getAppPath(), 'sample.py');
    const tempScriptPath = join(tmpdir(), 'sample.py');

    // Copy the Python script to a temporary directory
    await fs.copyFile(scriptPath, tempScriptPath);

    return new Promise((resolve, reject) => {
        console.log('Python script path:', tempScriptPath);
        execFile('python', [tempScriptPath, inputString], (error, stdout, stderr) => {
            if (error) {
                reject(error);
            } else {
                resolve(stdout.trim());
            }
        });
    });
}

function app_on() {
    ipcMain.on('send-message', async (event, message) => {
        try {
            const result = await callPythonReverseString(message);
            event.reply('receive-message', result);
        } catch (error) {
            console.error('Error calling Python script:', error);
            event.reply('receive-message', `Error: ${error.message}`);
        }
    });

    app.on('ready', createWindow);

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
}

function createWindow() {
    const mainWindow = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            preload: join(__dirname, 'preload.js'),
            contextIsolation: true,
            enableRemoteModule: false,
            nodeIntegration: false
        }
    });

    Menu.setApplicationMenu(null);
    mainWindow.loadFile('index.html');

    // Uncomment the following line to open DevTools by default
    // mainWindow.webContents.openDevTools();
}

app_on();