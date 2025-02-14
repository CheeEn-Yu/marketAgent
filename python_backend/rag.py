import os
import sys
import io
import json
import argparse
from google.cloud import aiplatform
from vertexai.preview import rag
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)

# 設定專案與區域
PROJECT_ID = PROJECT_ID
REGION = "us-central1"
aiplatform.init(project=PROJECT_ID, location=REGION)

# 設定標準輸出編碼（支援中文輸出）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_rag_pipeline(args, history, existing_corpus= f"projects/901172456759/locations/us-central1/ragCorpora/4467570830351532032"):
    """
    使用已部署的 Corpus 建立檢索工具、整合 RAG 模型並發送查詢。
    參數:
      prompt: 查詢內容
      model_name: 使用的生成模型名稱（預設 gemini-1.5-pro）
      existing_corpus: 已部署的 Corpus 的完整資源名稱（必填）
    """
    if not existing_corpus:
        raise ValueError("請提供已部署的 Corpus 的完整資源名稱，使用 --existing_corpus 參數")
    
    corpus = type("Corpus", (), {"name": existing_corpus})
    
    try:
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(rag_corpus=corpus.name)
                    ],
                    similarity_top_k=20,           # 設定檢索回傳的 top 5 筆結果
                    vector_distance_threshold=0.6,  # 可根據需要調整閥值
                ),
            )
        )
    except Exception as e:
        print("建立檢索工具時發生錯誤:", e)
        return
    
    # Step 7: 建立 RAG 模型，並將檢索工具加入
    try:
        rag_model = GenerativeModel(
            model_name=args.model_name,
            generation_config=GenerationConfig(
                temperature=args.temperature,
                max_output_tokens=args.max_output_tokens,
            ),
            tools=[rag_retrieval_tool]
        )
    except Exception as e:
        print("建立 RAG 模型時發生錯誤:", e)
        return
    
    try:
        chat = rag_model.start_chat(history=history)
        result = chat.send_message(args.prompt)
        print(result.candidates[0].content.parts[0].text)
    except Exception as e:
        print("發送查詢並生成回答時發生錯誤:", e)

def main():
    parser = argparse.ArgumentParser(description="Generate content using a generative model.")
    parser.add_argument("--prompt", type=str, default="Tell me how to win a hackathon", help="The prompt to send to the model.")
    parser.add_argument("--model_name", type=str, default="gemini-1.5-flash", help="The name of the generative model to use.")
    parser.add_argument("--max_output_tokens", type=int, default=2048, help="max output tokens of the generative model.")
    parser.add_argument("--temperature", type=float, default=0.5, help="temperature of the generative model.")
    parser.add_argument("--history", type=str, help="The name of the generative model to use.")
    
    args = parser.parse_args()
    history_dict = json.loads(args.history)

    content_list = []
    for item in history_dict:
        # Create Part object from the text in parts
        parts = [Part.from_text(part['text']) for part in item['parts']]
        # Create Content object with role and parts
        content = Content(role=item['role'], parts=parts)
        content_list.append(content)
    run_rag_pipeline(args, content_list)

if __name__ == "__main__":
    main()