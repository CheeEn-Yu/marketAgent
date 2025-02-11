import { getServerProfile } from "@/lib/server/server-chat-helpers"
import { ChatSettings } from "@/types"
import {
  FunctionDeclarationSchemaType,
  HarmBlockThreshold,
  HarmCategory,
  VertexAI
} from "@google-cloud/vertexai"

// import { VertexAI } from "@google-cloud/vertexai"
// export const runtime = "edge"
const project = PROJECT_ID;
const location = 'us-central1';
const textModel =  'gemini-1.5-flash';
const vertexAI = new VertexAI({project: project, location: location});
// Instantiate Gemini models
const generativeModel = vertexAI.getGenerativeModel({
    model: textModel,
    // The following parameters are optional
    // They can also be passed to individual content generation requests
    safetySettings: [{category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE}],
    generationConfig: {maxOutputTokens: 256},
    systemInstruction: {
      role: 'system',
      parts: [{"text": `you are a helpful customer service agent.`}]
    },
});

export async function POST(request: Request) {
  const json = await request.json()
  const { chatSettings, messages } = json as {
    chatSettings: ChatSettings
    messages: any[]
  }

  try {
    const lastMessage = messages.pop()
    const prompt = lastMessage.parts  // adjust if parts is not exactly a string
    
    const chat = generativeModel.startChat({
        history: messages,
        generationConfig: {
          temperature: chatSettings.temperature
        }
      }
    );

    // Get generated content from VertexAI.
    const streamingResult = await await chat.sendMessageStream(prompt[0].text);
    const encoder = new TextEncoder()
    const readableStream = new ReadableStream({
      async start(controller) {
        for await (const item of streamingResult.stream) {
          const chunkText = item.candidates[0].content.parts[0].text
          controller.enqueue(encoder.encode(chunkText))
          console.log(chunkText)
        }
        controller.close()
      }
    })
    return new Response(readableStream, {
      headers: { "Content-Type": "text/plain" }
    })

  } catch (error: any) {
    let errorMessage = error.message || "An unexpected error occurred"
    const errorCode = error.status || 500

    if (errorMessage.toLowerCase().includes("api key not found")) {
      errorMessage =
        "Vertex AI credentials not found. Please set them in your profile settings."
    }

    return new Response(JSON.stringify({ message: errorMessage }), {
      status: errorCode,
      headers: { "Content-Type": "application/json" }
    })
  }
}