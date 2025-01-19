import { app, BrowserWindow, ipcMain, Menu } from 'electron';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execFile } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function callPythonReverseString(inputString) {
    return new Promise((resolve, reject) => {
        execFile('python', [join(__dirname, 'sample.py'), inputString], (error, stdout, stderr) => {
            if (error) {
                reject(error);
            } else {
                resolve(stdout.trim());
            }
        });
    });
}

function app_on() {
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
}

app_on();