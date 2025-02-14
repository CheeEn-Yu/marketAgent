// Define interfaces for the API request/response types
interface ChatPart {
    text: string;
}

interface ChatMessage {
    role: string;
    parts: ChatPart[];
}

interface ChatRequest {
    prompt: string;
    model_name?: string;
    history?: ChatMessage[];
}

interface ChatResponse {
    response: string;
}

interface StreamChunk {
    chunk: string;
}

class ChatClient {
    private baseUrl: string;

    constructor(baseUrl: string = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    // Regular chat request
    async chat(request: ChatRequest): Promise<ChatResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(request),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error in chat request:', error);
            throw error;
        }
    }

    // Streaming chat request
    async *chatStream(request: ChatRequest): AsyncGenerator<string, void, unknown> {
        try {
            const response = await fetch(`${this.baseUrl}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(request),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body!.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk: StreamChunk = JSON.parse(decoder.decode(value));
                yield chunk.chunk;
            }
        } catch (error) {
            console.error('Error in chat stream:', error);
            throw error;
        }
    }
}

// Example usage
async function example() {
    const client = new ChatClient();

    // Example 1: Regular chat request
    try {
        const response = await client.chat({
            prompt: "Tell me how to win a hackathon",
            model_name: "gemini-1.5-flash"
        });
        console.log('Regular response:', response.response);
    } catch (error) {
        console.error('Regular chat error:', error);
    }

    // Example 2: Streaming chat request
    // try {
    //     const streamingResponse = client.chatStream({
    //         prompt: "Tell me how to win a hackathon",
    //         model_name: "gemini-1.5-flash"
    //     });

    //     for await (const chunk of streamingResponse) {
    //         console.log('Streaming chunk:', chunk);
    //     }
    // } catch (error) {
    //     console.error('Streaming chat error:', error);
    // }
}

// Run the example
example();