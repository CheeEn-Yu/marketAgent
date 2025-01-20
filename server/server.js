const http = require('http');
const { spawn } = require('child_process');

let pythonProcess;

// Function to start the Python process and keep it running
function startPythonProcess() {
    const process = spawn('conda', ['run', '-n', 'agent', 'python', 'sample.py'], {
        stdio: ['pipe', 'pipe', 'pipe'], // Pipe stdin, stdout, and stderr for communication
    });

    process.on('error', (err) => {
        console.error('Failed to start Python process:', err);
    });

    process.on('exit', (code, signal) => {
        console.error(`Python process exited with code ${code} and signal ${signal}`);
        pythonProcess = null; // Reset pythonProcess so that the server knows it's unavailable
    });

    return process;
}

// Function to send input to the Python process and get the response
function sendToPython(input) {
    return new Promise((resolve, reject) => {
        if (!pythonProcess) {
            reject(new Error('Python process is not running.'));
            return;
        }

        let output = '';
        const handleStdout = (data) => {
            output += data.toString();
        };

        const handleStderr = (err) => {
            reject(err.toString());
        };

        const handleStdoutEnd = () => {
            resolve(output.trim());
            cleanup(); // Clean up listeners
        };

        const cleanup = () => {
            pythonProcess.stdout.off('data', handleStdout);
            pythonProcess.stdout.off('end', handleStdoutEnd);
            pythonProcess.stderr.off('data', handleStderr);
        };

        pythonProcess.stdout.on('data', handleStdout);
        pythonProcess.stdout.on('end', handleStdoutEnd);
        pythonProcess.stderr.on('data', handleStderr);

        pythonProcess.stdin.write(`${input}\n`);
    });
}

// Create the server
const server = http.createServer(async (req, res) => {
    if (req.method === 'POST') {
        let body = '';

        req.on('data', (chunk) => {
            body += chunk.toString();
        });

        req.on('end', async () => {
            console.log('Received input:', body);

            try {
                const result = await sendToPython(body);
                res.writeHead(200, { 'Content-Type': 'text/plain' });
                res.end(result); // Respond with the Python script's output
            } catch (error) {
                console.error('Error processing input:', error);
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Error processing your request.');
            }
        });
    } else {
        res.writeHead(405, { 'Content-Type': 'text/plain' });
        res.end('Only POST method is supported');
    }
});

const PORT = 8080;

// Start the server and Python process
server.listen(PORT, () => {
    console.log(`Server is listening on port ${PORT}`);
    pythonProcess = startPythonProcess();
    if (pythonProcess) {
        console.log('Python process started and model loaded.');
    } else {
        console.error('Failed to start Python process.');
    }
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('Shutting down...');
    if (pythonProcess) {
        pythonProcess.kill();
    }
    process.exit();
});
