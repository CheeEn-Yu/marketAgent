from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import vertexai
from fastapi.responses import StreamingResponse
from vertexai.generative_models import (
    Content,
    GenerativeModel,
    Part,
)

# Initialize FastAPI app
app = FastAPI(title="Vertex AI Chat API")

# Pydantic models for request validation
class ChatPart(BaseModel):
    text: str

class ChatMessage(BaseModel):
    role: str
    parts: List[ChatPart]

class ChatRequest(BaseModel):
    prompt: str
    model_name: str = "gemini-1.5-flash"
    history: Optional[List[ChatMessage]] = None

# Initialize Vertex AI
PROJECT_ID = PROJECT_ID
REGION = "us-central1"
vertexai.init(project=PROJECT_ID, location=REGION)

@app.post("/chat")
async def generate_chat_response(request: ChatRequest):
    try:
        # Initialize the model
        model = GenerativeModel(request.model_name)
        
        # Process history if provided
        content_list = []
        if request.history:
            for item in request.history:
                # Convert each history item to Vertex AI Content object
                parts = [Part.from_text(part.text) for part in item.parts]
                content = Content(role=item.role, parts=parts)
                content_list.append(content)
        
        # Start chat with history if available
        chat = model.start_chat(history=content_list if content_list else None)
        
        # Send message and get response
        response = chat.send_message(request.prompt)
        
        # Return the response
        return {
            "response": response.candidates[0].content.parts[0].text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def generate_chat_response_stream(request: ChatRequest):
    try:
        # Initialize the model
        model = GenerativeModel(request.model_name)
        
        # Process history if provided
        content_list = []
        if request.history:
            for item in request.history:
                parts = [Part.from_text(part.text) for part in item.parts]
                content = Content(role=item.role, parts=parts)
                content_list.append(content)
        
        # Start chat with history if available
        chat = model.start_chat(history=content_list if content_list else None)
        
        # Send message and get streaming response
        response = chat.send_message(request.prompt, stream=True)
        
        # Stream the response
        async def response_generator():
            for chunk in response:
                yield {
                    "chunk": chunk.candidates[0].content.parts[0].text
                }
        
        return StreamingResponse(response_generator(), media_type="text/plain")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # curl -X POST "http://localhost:8000/chat/stream" -H "Content-Type: application/json" -d '{    "prompt": "Tell me how to win a hackathon"}'