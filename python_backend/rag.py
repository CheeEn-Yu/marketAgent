import os
import sys
import io
import json
import argparse
from google.cloud import aiplatform
from langchain_google_vertexai import VertexAI
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_csv_agent
from vertexai.preview import rag
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)

PROJECT_ID = PROJECT_ID
REGION = "us-central1"
aiplatform.init(project=PROJECT_ID, location=REGION)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def csv_agent(model, csv_file, prompt):
    agent = create_csv_agent(
        model,
        csv_file,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        allow_dangerous_code=True,
    )
    return agent.run(prompt)


def main_worker(args, history):
    """
    使用已部署的 Corpus 建立檢索工具、整合 RAG 模型並發送查詢。
    參數:
      prompt: 查詢內容
      user_role: 使用者角色，決定使用哪個 Corpus。可選值有 "Global", "China", "Korea"
      model_name: 使用的生成模型名稱（預設 gemini-1.5-pro）
    """
    # 根據不同的 user_role 指定對應的 Corpus 資源名稱
    corpus_dict = {
        "Global": "projects/901172456759/locations/us-central1/ragCorpora/4467570830351532032",
        "China": "projects/901172456759/locations/us-central1/ragCorpora/8142508126285856768",
        "Korea": "projects/901172456759/locations/us-central1/ragCorpora/1224979098644774912",
    }
    
    if args.user_role not in corpus_dict:
        raise ValueError("無效的 user_role，請選擇 Global、China 或 Korea")
    
    existing_corpus = corpus_dict[args.user_role]
    
    # 利用已部署的 Corpus 名稱建立一個簡單的對象，以便後續傳入 RAG SDK
    corpus = type("Corpus", (), {"name": existing_corpus})
    try:
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(rag_corpus=corpus.name)
                    ],
                    similarity_top_k=20,
                    vector_distance_threshold=0.6,
                ),
            )
        )
        # csv_agent_tool = FunctionDeclaration(
        #     name="csv_agent",
        #     description="Answer any question with a CSV file",
        # )
    except Exception as e:
        print("建立檢索工具時發生錯誤:", e)
        return
    
    # create csv agent inside function calling

    
    try:
        model = VertexAI(
            model_name=args.model_name,
            generation_config=GenerationConfig(
                temperature=args.temperature if args.temperature else 0.5,
                max_output_tokens=args.max_tokens if args.max_tokens else 100,
            ),
            tools=[rag_retrieval_tool]
        )
        chat = model.client.start_chat(history=history)
        response = chat.send_message(args.prompt)
        print(response.candidates[0].content.parts[0].text)

    except Exception as e:
        print("發送查詢並生成回答時發生錯誤:", e)
        return
    
def main():
    parser = argparse.ArgumentParser(description="Generate content using a generative model.")
    parser.add_argument("--prompt", type=str, default="Tell me how to win a hackathon", help="The prompt to send to the model.")
    parser.add_argument("--model_name", type=str, default="gemini-1.5-pro", help="The name of the generative model to use.")
    parser.add_argument("--history", type=str, help="History JSON string")
    parser.add_argument("--temperature", type=float, help="The temperature to use when sampling from the model.")
    parser.add_argument("--max_tokens", type=int, help="The maximum number of tokens to generate.")
    parser.add_argument("--user_role", type=str, default="Global", choices=["Global", "China", "Korea"], help="According to user role to select Corpus")
    parser.add_argument("--is_sum_mode", type=bool, default=False, help="Whether to use summarization mode")
    parser.add_argument("--sum_mode_company", type=str, default="", help="The company name to summarize")
    parser.add_argument("--sum_mode_year", type=str, default="", help="The year to summarize")
    parser.add_argument("--sum_mode_quarter", type=str, default="Q1", help="The quarter to summarize")
    args = parser.parse_args()
    
    history_dict = json.loads(args.history) if args.history else []
    
    model = GenerativeModel(args.model_name)
    content_list = []
    for item in history_dict:
        # Create Part object from the text in parts
        parts = [Part.from_text(part['text']) for part in item.get('parts', [])]
        # Create Content object with role and parts
        content = Content(role=item.get('role', 'user'), parts=parts)
        content_list.append(content)
    
    # chat = model.start_chat(history=content_list)
    # response = chat.send_message(args.prompt)
    # print(response.candidates[0].content.parts[0].text)
    
    main_worker(args, content_list)

if __name__ == "__main__":
    main()
