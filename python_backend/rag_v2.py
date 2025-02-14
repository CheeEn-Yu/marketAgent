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

def run_rag_pipeline(prompt, user_role, model_name="gemini-1.5-pro"):
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
        "China": "projects/901172456759/locations/us-central1/ragCorpora/8142508126285856768",  # 請將 CHINA_CORPUS_ID 換成實際的 Corpus ID
        "Korea": "projects/901172456759/locations/us-central1/ragCorpora/1224979098644774912",  # 請將 KOREA_CORPUS_ID 換成實際的 Corpus ID
    }
    
    if user_role not in corpus_dict:
        raise ValueError("無效的 user_role，請選擇 Global、China 或 Korea")
    
    existing_corpus = corpus_dict[user_role]
    
    # 利用已部署的 Corpus 名稱建立一個簡單的對象，以便後續傳入 RAG SDK
    corpus = type("Corpus", (), {"name": existing_corpus})
    # print("使用已部署的 Corpus：", corpus.name)
    
    # Step 6: 建立 Retrieval 物件並用 Tool.from_retrieval 包裝
    try:
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        # 傳入完整的 Corpus 資源名稱
                        rag.RagResource(rag_corpus=corpus.name)
                    ],
                    similarity_top_k=20,           # 設定檢索回傳的 top 20 筆結果
                    vector_distance_threshold=0.6,  # 可根據需要調整閥值
                ),
            )
        )
        # print("Step 6: 檢索工具建立成功。")
    except Exception as e:
        print("建立檢索工具時發生錯誤:", e)
        return
    
    # Step 7: 建立 RAG 模型，並將檢索工具加入
    try:
        rag_model = GenerativeModel(
            model_name=model_name,
            tools=[rag_retrieval_tool]
        )
        # print("Step 7: RAG 模型建立成功。")
    except Exception as e:
        print("建立 RAG 模型時發生錯誤:", e)
        return
    
    # Step 8: 發送查詢並取得生成回答
    try:
        # print("Step 8: 發送查詢並取得生成回答")
        # print("查詢內容:", prompt)
        result = rag_model.generate_content(prompt)
        print("result:", result)
        # print("查詢完成。")
        print(result.text)
    except Exception as e:
        print("發送查詢並生成回答時發生錯誤:", e)

def main():
    parser = argparse.ArgumentParser(description="Generate content using a generative model.")
    parser.add_argument("--prompt", type=str, default="Tell me how to win a hackathon", help="The prompt to send to the model.")
    parser.add_argument("--model_name", type=str, default="gemini-1.5-flash", help="The name of the generative model to use.")
    parser.add_argument("--history", type=str, help="History JSON string")
    parser.add_argument("--user_role", type=str, default="Global", choices=["Global", "China", "Korea"], help="使用者角色，決定使用的 Corpus")
    
    args = parser.parse_args()
    
    # 解析 history 參數，假設它是一個 JSON 格式的字串
    history_dict = json.loads(args.history) if args.history else []
    
    # 這邊如果需要使用聊天模型，將歷史對話加入聊天內容
    model = GenerativeModel(args.model_name)
    content_list = []
    for item in history_dict:
        # Create Part object from the text in parts
        parts = [Part.from_text(part['text']) for part in item.get('parts', [])]
        # Create Content object with role and parts
        content = Content(role=item.get('role', 'user'), parts=parts)
        content_list.append(content)
    
    chat = model.start_chat(history=content_list)
    # 若你有需要進行聊天查詢，可以啟用下列註解程式碼
    # response = chat.send_message(args.prompt)
    # print(response.candidates[0].content.parts[0].text)
    
    # 根據傳入的 user_role 呼叫 RAG Pipeline
    run_rag_pipeline(args.prompt, args.user_role, model_name=args.model_name)

if __name__ == "__main__":
    main()
