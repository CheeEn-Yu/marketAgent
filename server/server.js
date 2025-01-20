const http = require('http');
const { spawn } = require('child_process');

let pythonProcess;
let isPythonReady = false;

function startPythonProcess() {
    console.log('Starting Python process...');

    // make sure to activate the environment before running node server.js
    const process = spawn('python', ['sample.py'], {
        stdio: ['pipe', 'pipe', 'pipe'],
    });

    // Handle Python's stdout
    process.stdout.on('data', (data) => {
        const output = data.toString().trim();
        console.log('Python stdout:', output);
        
        if (output.includes('PYTHON_READY')) {
            console.log('Python process is ready to accept input');
            isPythonReady = true;
        }
    });

    // Handle Python's stderr (where our logs go)
    process.stderr.on('data', (data) => {
        console.log('Python log:', data.toString().trim());
    });

    process.on('error', (err) => {
        console.error('Failed to start Python process:', err);
        isPythonReady = false;
    });

    process.on('exit', (code, signal) => {
        console.error(`Python process exited with code ${code} and signal ${signal}`);
        isPythonReady = false;
        pythonProcess = null;
    });

    return process;
}

function sendToPython(input) {
    return new Promise((resolve, reject) => {
        if (!pythonProcess || !isPythonReady) {
            reject(new Error('Python process is not ready.'));
            return;
        }

        let responseBuffer = '';
        let isCollecting = false;
        const timeout = setTimeout(() => {
            cleanup();
            reject(new Error('Timeout waiting for Python response'));
        }, 60000);

        console.log('Sending to Python:', input);

        const handleStdout = (data) => {
            const lines = data.toString().split('\n');
            console.log('Received from Python:', lines);
            
            for (const line of lines) {
                if (line.includes('RESPONSE_START')) {
                    console.log('Starting to collect response');
                    isCollecting = true;
                    responseBuffer = '';
                } else if (line.includes('RESPONSE_END')) {
                    console.log('Finished collecting response');
                    isCollecting = false;
                    clearTimeout(timeout);
                    cleanup();
                    resolve(responseBuffer.trim());
                } else if (isCollecting) {
                    responseBuffer += line + '\n';
                }
            }
        };

        const handleStderr = (data) => {
            console.log('Python error/log:', data.toString().trim());
        };

        const cleanup = () => {
            pythonProcess.stdout.removeListener('data', handleStdout);
            pythonProcess.stderr.removeListener('data', handleStderr);
        };

        pythonProcess.stdout.on('data', handleStdout);
        pythonProcess.stderr.on('data', handleStderr);

        try {
            pythonProcess.stdin.write(`${input}\n`);
        } catch (error) {
            cleanup();
            clearTimeout(timeout);
            reject(error);
        }
    });
}

const server = http.createServer(async (req, res) => {
    if (req.method === 'POST') {
        let body = '';

        req.on('data', (chunk) => {
            body += chunk.toString();
        });

        req.on('end', async () => {
            console.log('Received HTTP request with input:', body);

            if (!isPythonReady) {
                console.log('Python is not ready, sending 503 response');
                res.writeHead(503, { 'Content-Type': 'text/plain' });
                res.end('Server is not ready yet. Please try again later.');
                return;
            }

            try {
                const result = await sendToPython(body);
                console.log('Sending response to client:', result);
                res.writeHead(200, { 'Content-Type': 'text/plain' });
                res.end(result);
            } catch (error) {
                console.error('Error processing input:', error);
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Error processing your request: ' + error.message);
            }
        });
    } else {
        res.writeHead(405, { 'Content-Type': 'text/plain' });
        res.end('Only POST method is supported');
    }
});

const PORT = 8080;

server.listen(PORT, () => {
    console.log(`Server is listening on port ${PORT}`);
    pythonProcess = startPythonProcess();
});

process.on('SIGINT', () => {
    console.log('Shutting down...');
    if (pythonProcess) {
        pythonProcess.stdin.end();
        pythonProcess.kill();
    }
    server.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
});