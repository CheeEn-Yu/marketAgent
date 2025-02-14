import { spawn } from 'child_process';

function executePythonScript(): Promise<string> {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', ['test.py', '--prompt', 'Hello, World!']);
        let outputData = '';

        pythonProcess.stdout.on('data', (data) => {
            outputData += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            console.error(`Error: ${data}`);
        });

        pythonProcess.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Python process exited with code ${code}`));
                return;
            }
            resolve(outputData);
        });
    });
}

async function main() {
    try {
        const output = await executePythonScript();
        console.log('Python script output:');
        console.log(output);
    } catch (error) {
        console.error('Failed to execute Python script:', error);
    }
}

main();