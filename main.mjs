import { app, BrowserWindow, ipcMain, Menu, dialog } from 'electron';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execFile } from 'child_process';
import { promises as fs } from 'fs';
import { tmpdir } from 'os';
import http from 'http';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function sendMessageToServer(message) {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: '140.112.252.40', // Replace with the actual remote IP
            port: 8080,                // Port number
            path: '/',                 // Path on the server (e.g., `/`)
            method: 'POST',            // HTTP method
            headers: {
                'Content-Type': 'text/plain',
                'Content-Length': Buffer.byteLength(message),
            },
        };

        const req = http.request(options, (res) => {
            let responseData = '';

            res.setEncoding('utf8');
            res.on('data', (chunk) => {
                responseData += chunk;
            });

            res.on('end', () => {
                if (res.statusCode === 200) {
                    resolve(responseData.trim());
                } else {
                    reject(new Error(`Server responded with status code: ${res.statusCode}`));
                }
            });
        });

        req.on('error', (err) => {
            reject(err);
        });

        // Write the message body and end the request
        req.write(message);
        req.end();
    });
}

async function callServerFunction(inputString) {
    try {
        const result = await sendMessageToServer(inputString);
        return result;
    } catch (error) {
        throw new Error(`Failed to communicate with server: ${error.message}`);
    }
}

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
    ipcMain.handle('open-directory-dialog', async (event) => {
        const result = await dialog.showOpenDialog({
            properties: ['open-file']
        });
        return result.filePaths;
    });

    ipcMain.on('send-message', async (event, message) => {
        try {
            const result = await callServerFunction(message);
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