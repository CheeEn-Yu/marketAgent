from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerativeModel,
    Part,
    Tool,
)
import vertexai
from vertexai.generative_models import GenerativeModel
import argparse
import sys
import io
import json

PROJECT_ID = PROJECT_ID
REGION = "us-central1"
vertexai.init(project=PROJECT_ID, location=REGION)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
def main():
    parser = argparse.ArgumentParser(description="Generate content using a generative model.")
    parser.add_argument("--prompt", type=str, default="Tell me how to win a hackathon", help="The prompt to send to the model.")
    parser.add_argument("--model_name", type=str, default="gemini-1.5-flash", help="The name of the generative model to use.")
    # parser.add_argument("--history", type=str, help="The name of the generative model to use.")
    

    args = parser.parse_args()
    history_dict = json.loads(args.history)

    model = GenerativeModel(args.model_name)
    content_list = []
    for item in history_dict:
        # Create Part object from the text in parts
        parts = [Part.from_text(part['text']) for part in item['parts']]
        # Create Content object with role and parts
        content = Content(role=item['role'], parts=parts)
        content_list.append(content)
    chat = model.start_chat()
    response = chat.send_message(
        args.prompt,
        stream=True
    )
    for item in response:
        print(item.candidates[0].content.parts[0].text, end='')
    # For non-streaming response
    # print(response.candidates[0].content.parts[0].text)

if __name__ == "__main__":
    main()


