import os
import sys
import io
import json
import uuid
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from google.cloud import aiplatform, storage
from langchain_google_vertexai import VertexAI
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_csv_agent
from vertexai.preview import rag
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    ToolConfig,
    GenerativeModel,
    Part,
    Tool,
)

PROJECT_ID = PROJECT_ID
REGION = "us-central1"
aiplatform.init(project=PROJECT_ID, location=REGION)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_csv_from_bucket(bucket_name, blob_name):
    """
    從指定的 bucket 讀取 CSV 檔案內容，並將內容印出，不需先下載到本地端。
    
    :param bucket_name: bucket 的名稱
    :param blob_name: CSV 檔案在 bucket 中的路徑或名稱
    """
    # 建立 Storage client
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    # 直接從 blob 讀取資料（bytes 格式），並解碼成字串
    csv_bytes = blob.download_as_string()
    csv_str = csv_bytes.decode('utf-8')
    
    # 使用 io.StringIO 將字串轉換成檔案物件，供 csv.reader 使用
    csv_file = io.StringIO(csv_str)
    return csv_file

def load_and_categorize(file_path):
    df = pd.read_csv(file_path)
    
    #categories
    companies = df['Company Name'].unique()
    indices = df['Index'].unique()
    years = df['CALENDAR_YEAR'].unique()
    quarters = df['CALENDAR_QTR'].unique()
    
    
    categories = {
        "Companies": companies,
        "Indices": indices,
        "Years": years,
        "Quarters": quarters
    }
    
    return df, categories

def validate_time_format(time_str, default):
    """檢查 YYYY_QX 或 YYYY Q 格式，例如 '2023_Q3' 或 '2023 Q3'"""
    if "_" in time_str:
        parts = time_str.split("_")
        if len(parts) == 2 and parts[0].isdigit() and parts[1][0] == 'Q' and parts[1][1].isdigit():
            year, quarter = int(parts[0]), int(parts[1][1])
            if 1 <= quarter <= 4:
                return f"{year}_Q{quarter}"
    elif " " in time_str:
        parts = time_str.split(" ")
        if len(parts) == 2 and parts[0].isdigit() and parts[1][0] == 'Q' and parts[1][1].isdigit():
            year, quarter = int(parts[0]), int(parts[1][1])
            if 1 <= quarter <= 4:
                return f"{year}_Q{quarter}"
    #print(f"Error: Invalid time format '{time_str}', expected 'YYYY_QX' or 'YYYY Q'. Using default: {default}")
    return default

def parse_user_query_with_gemini(query, model, get_plot_args):
    try:
        plot_tool = Tool(
            function_declarations=[get_plot_args],
        )
        response = model.generate_content(
            query,
            tools=[plot_tool],  
            tool_config=ToolConfig(
                function_calling_config=ToolConfig.FunctionCallingConfig(
                    mode=ToolConfig.FunctionCallingConfig.Mode.ANY,
                )
            )
        )
        
        if not response or not response.candidates:
            #print("No functional response from Gemini")
            return None

        candidate = response.candidates[0]

        if not candidate.content.parts:
            return None

        response_part = candidate.content.parts[0]
        
        if hasattr(response_part, "function_call") and response_part.function_call:
            function_call = response_part.function_call
            function_args = function_call.args  
            
            if not function_args:
                return None

            # **確保 index 是 list**
            if "index" in function_args:
                function_args["index"] = function_args["index"].split(", ") if isinstance(function_args["index"], str) else [function_args["index"]]


            if "start_time" in function_args:
                function_args["start_time"] = validate_time_format(function_args["start_time"], "2020_Q1")

            if "end_time" in function_args:
                function_args["end_time"] = validate_time_format(function_args["end_time"], "2024_Q3")
            
            if function_args['start_time'] < "2020_Q1" or function_args['end_time'] > "2024_Q3":
                return "Time range is out of data. Our data range is from 2020 Q1 to 2024 Q3. Please input the correct time range query."

            # **儲存結果**
            with open("gemini_parsed_output.json", "w", encoding="utf-8") as json_file:
                json.dump(function_args, json_file, indent=4, ensure_ascii=False)

            return function_args  

        else:
            return None

    except Exception as e:
        return None


def plot_financial_data(df, parsed_query):
    """
    繪製指定公司與財務指標的季度折線圖。

    參數:
    df (pd.DataFrame): 包含財務數據的 DataFrame。
    company_name (str): 要篩選的公司名稱 (如 "Apple")。
    index_name (str): 要繪製的財務指標 (如 "Revenue")。
    """
    #print(parsed_query)
    # 篩選數據
    company_name = parsed_query.get("company" , "")
    index = parsed_query.get("index" , "")
    start_time = parsed_query.get("start_time", "")
    end_time = parsed_query.get("end_time" , "")
    t = df[["CALENDAR_YEAR", "CALENDAR_QTR"]].astype(str).agg("_".join, axis=1)

    
    company_name_series = pd.Series([company_name] * len(t))
    index_series = pd.Series([index] * len(t))
    end_time_series = pd.Series([end_time] * len(t))
    start_time_series = pd.Series([start_time] * len(t))

    #  & (t <= end_time_series) & (t >= start_time_series)
    filtered_df = df[(df["Company Name"] == company_name) & (df["Index"] == index[0]) & (t <= end_time_series) & (t >= start_time_series)]
    
    if filtered_df.empty:
        return None
    
    # 確保數據排序
    filtered_df = filtered_df.sort_values(by=["CALENDAR_YEAR", "CALENDAR_QTR"])

    # 設定 x 軸標籤
    x_labels = [f"{year}_{qtr}" for year, qtr in zip(filtered_df["CALENDAR_YEAR"], filtered_df["CALENDAR_QTR"])]

    save_dir = "Line_Chart"
    
    filepath = f"{save_dir}/Financial_line_chart_{uuid.uuid4().hex}.png"
    os.makedirs(save_dir, exist_ok=True)
    # 繪製折線圖
    plt.figure(figsize=(10, 6))
    plt.plot(x_labels, filtered_df["USD_Value"], marker="o", linestyle="-", label=index)

    # 設定標籤與標題
    plt.xlabel("Year_Quarter")
    plt.ylabel(f"{index[0]} (USD Million)")
    plt.title(f"{company_name} {index[0]} from {start_time} to {end_time}")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.savefig(filepath)
    plt.close()

    return filepath


def csv_agent(args, csv_file_path):
    model = VertexAI(model_name=args.model_name)
    agent = create_csv_agent(
        model,
        csv_file_path,
        verbose=False,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        allow_dangerous_code=True,
    )
    return agent.run(args.prompt)

def rag_agent(args, rag_retrieval_tool):
    try:
        model = GenerativeModel(
            model_name=args.model_name,
            generation_config=GenerationConfig(
                temperature=args.temperature if args.temperature else 0.5,
                max_output_tokens=args.max_tokens if args.max_tokens else 100,
            ),
            tools=[rag_retrieval_tool]
        )
        response = model.generate_content(args.prompt, tools=[rag_retrieval_tool])
        response_part = response.candidates[0].content.parts[0]
        return response_part.text

    except Exception as e:
        print("生成RAG回答時發生錯誤:", e)
        return



def main_worker(args, history):
    """
    使用已部署的 Corpus 建立檢索工具、整合 RAG 模型並發送查詢。
    參數:
      prompt: 查詢內容
      user_role: 使用者角色，決定使用哪個 Corpus。可選值有 "Global", "China", "Korea"
      model_name: 使用的生成模型名稱
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
        topk = 20 if args.user_role == "Global" else 10
        rag_retrieval_tool = Tool.from_retrieval(
            retrieval=rag.Retrieval(
                source=rag.VertexRagStore(
                    rag_resources=[
                        rag.RagResource(rag_corpus=corpus.name)
                    ],
                    similarity_top_k=topk,
                    vector_distance_threshold=0.6,
                ),
            )
        )
        get_plot_func = FunctionDeclaration(
            name="plot_line_chart",
            description="Draw a line chart of the financial index for a company according to the user's query, including the start and end time, which are in the format 'year_quarter, showing the financial index for each quarter.",
            parameters={
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "string of company name include ['Amazon', 'AMD', 'Amkor', 'Apple', 'Applied Material', 'Baidu', 'Broadcom', 'Cirrus Logic', 'Google', 'Himax', 'Intel', 'KLA', 'Marvell', 'Microchip', 'Microsoft', 'Nvidia', 'ON Semi', 'Qorvo', 'Qualcomm', 'Samsung', 'STM', 'Tencent', 'Texas Instruments', 'TSMC', 'Western Digital'],\
                        如果使用者輸入的是中文，公司名稱範圍:[亞馬遜', '超微', '艾克爾國際科技', '蘋果', '應用材料', '百度', '博通', '思睿邏輯', '谷歌', '奇景光電', '英特爾', '科磊', '邁威爾科技', '微芯科技', '微軟', '輝達', '安森美', '威訊聯合半導體', '高通公司', '三星', '意法半導體', '騰訊', '德州儀器', '台灣積體電路製造', '威騰電子']. 請轉換成 ['Amazon', 'AMD', 'Amkor', 'Apple', 'Applied Material', 'Baidu', 'Broadcom', 'Cirrus Logic', 'Google', 'Himax', 'Intel', 'KLA', 'Marvell', 'Microchip', 'Microsoft', 'Nvidia', 'ON Semi', 'Qorvo', 'Qualcomm', 'Samsung', 'STM', 'Tencent', 'Texas Instruments', 'TSMC', 'Western Digital']\
                        If user assign other company name, return out of data"
                },
                "index": {
                    "type": "string",
                    "description": "index arguement means the finacial index that you want to extract from the raw data frame\
                        string of index include ['Cost of Goods Sold', 'Operating Expense', 'Operating Income', 'Revenue', 'Tax Expense', 'Total Asset' , 'Gross profit margin' , 'Operating margin']. \
                        User can input more than one index. For example, user_query = '我想知道 Apple 在 2023 的 revenue 和 Cost of Goods Sold', you should return like this format ['Revenue' , 'Cost of Goods Sold']\
                        So if user give multiple indeces input, return the list of indeces. \
                        If user assign other index name, return out of data. \
                        如果使用者輸入的是中文，指標名稱範圍['銷貨成本', '營業費用', '營業收入', '營收', '稅費', '總資產', '毛利率', '營業利益率']，將它轉化成  ['Cost of Goods Sold', 'Operating Expense', 'Operating Income', 'Revenue', 'Tax Expense', 'Total Asset' , 'Gross profit margin' , 'Operating margin']"
                },
                "start_time": {
                    "type": "string",
                    "description": "user can assign the start time of the data, the format should be 'year_quarter', for example '2020 Q1' means 2020 Q1, then you should return 2020_Q1.\
                        If user assign 'all' or not assign, return 2020_Q1. \
                        如果使用者輸入的是中文，請對應以下的時間格式，例如'2020 Q1'代表2020年第一季，則你應該回傳2020_Q1。\
                        if user assign other time, return out of data"
                },
                "end_time": {
                    "type": "string",
                    "description": "user can assign the end time of the data, the format should be 'year_quarter', for example '2023 Q4' means 2023 Q4, then you should return 2023_Q4.\
                        If user assign 'all' or not assign, return 2024_Q3. \
                        如果使用者輸入的是中文，請對應以下的時間格式，例如'2023 Q4'代表2023年第四季，則你應該回傳2023_Q4。\
                        if user assign other time, return out of data"
                },
            },
                "required": [
                    "company",
                    "index",
                    "start_time",
                    "end_time"
                ]
        }
        )

        rag_retrieval_func = FunctionDeclaration(
            name="rag_retrieval",
            description="""If you need more information about the topic, call this function to access RAG model.
            如果題目是針對法說會的問題，呼叫此函數以存取 RAG 模型，取得法說會逐字稿。""",
            parameters={
                "type": "object",
                "properties": {}
            },
        )
        csv_agent_func = FunctionDeclaration(
            name="csv_agent",
            description="If you need more information about finantial data, like ['Cost of Goods Sold', 'Operating Expense', 'Operating Income', 'Revenue', 'Tax Expense', 'Total Asset' , 'Gross profit margin' , 'Operating margin'], call this function to access csv data.",
            parameters={
                "type": "object",
                "properties": {}
            },
        )
        tool_kit = Tool(function_declarations=[csv_agent_func, rag_retrieval_func, get_plot_func])
    except Exception as e:
        print("建立檢索工具時發生錯誤:", e)
        return
    
    try:
        model = GenerativeModel(
            model_name=args.model_name,
            generation_config=GenerationConfig(
                temperature=args.temperature if args.temperature else 0.5,
                max_output_tokens=args.max_tokens if args.max_tokens else 100,
            ),
            tools=[tool_kit]
        )
        response = model.generate_content("如果是針對法說會的問題，call rag_retrieval。如果使用者問各種指標，call csv_agent來從database load相關資料來回答。如果使用者要求畫折線圖(line plot)，call plot_line_chart。以下為使用者問題:"+args.prompt, tools=[tool_kit], tool_config=ToolConfig(
                function_calling_config=ToolConfig.FunctionCallingConfig(
                    mode=ToolConfig.FunctionCallingConfig.Mode.ANY,
                )
            ))
        response_part = response.candidates[0].content.parts[0]
        if args.user_role == "Global":
            bucket_name = "careerhack2025-bsid-resource-bucket"
            blob_name = "FIN_Data.csv"
        else:
            bucket_name = "tsmccareerhack2025-bsid-grp6-bucket"
            blob_name = f"{args.user_role}_Fin_data.csv"
        csv_file_path = load_csv_from_bucket(bucket_name, blob_name)
        if hasattr(response_part, 'function_call') and response_part.function_call:
            if response_part.function_call.name == "csv_agent":
                print("Call csv_agent function")
                response = csv_agent(args, csv_file_path)
                print(response)
            elif response_part.function_call.name == "rag_retrieval":
                print("Call rag_retrieval function")
                response = rag_agent(args, rag_retrieval_tool)
                print(response)
            elif response_part.function_call.name == "plot_line_chart":
                df, _ = load_and_categorize(csv_file_path)
                parsed_query = parse_user_query_with_gemini(args.prompt, model, get_plot_func)
                if parsed_query:
                    path = plot_financial_data(df, parsed_query)
                    print(path)
                else:
                    print("Error : Failed to parse query")
        else:
            print(response_part.text)
        # chat = model.client.start_chat(history=history)
        # response = chat.send_message(args.prompt)
        # print(response.candidates[0].content.parts)


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
    
    content_list = []
    for item in history_dict:
        # Create Part object from the text in parts
        parts = [Part.from_text(part['text']) for part in item.get('parts', [])]
        # Create Content object with role and parts
        content = Content(role=item.get('role', 'user'), parts=parts)
        content_list.append(content)
    content_list.append(Content(role='user', parts=[Part.from_text(args.prompt)]))
    # chat = model.start_chat(history=content_list)
    # response = chat.send_message(args.prompt)
    # print(response.candidates[0].content.parts[0].text)
    
    main_worker(args, content_list)

if __name__ == "__main__":
    main()
