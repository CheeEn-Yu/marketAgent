import pandas as pd
import matplotlib.pyplot as plt
import json
from google.cloud import aiplatform
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerativeModel,
    Tool,
    ToolConfig
)

PROJECT_ID = PROJECT_ID
REGION = "us-central1"
aiplatform.init(project=PROJECT_ID, location=REGION)

model = GenerativeModel("gemini-1.5-pro-001")

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


get_plot_args = FunctionDeclaration(
    name="plot_line_chart",
    description="Get the exchange rate for currencies between countries",
    parameters={
    "type": "object",
    "properties": {
        "company": {
            "type": "string",
            "description": "string of company name include ['Amazon', 'AMD', 'Amkor', 'Apple', 'Applied Material', 'Baidu', 'Broadcom', 'Cirrus Logic', 'Google', 'Himax', 'Intel', 'KLA', 'Marvell', 'Microchip', 'Microsoft', 'Nvidia', 'ON Semi', 'Qorvo', 'Qualcomm', 'Samsung', 'STM', 'Tencent', 'Texas Instruments', 'TSMC', 'Western Digital'],\
                如果使用者輸入的是中文，請對應以下的公司名稱；[亞馬遜', '超微', '艾克爾國際科技', '蘋果', '應用材料', '百度', '博通', '思睿邏輯', '谷歌', '奇景光電', '英特爾', '科磊', '邁威爾科技', '微芯科技', '微軟', '輝達', '安森美', '威訊聯合半導體', '高通公司', '三星', '意法半導體', '騰訊', '德州儀器', '台灣積體電路製造', '威騰電子']. \
                If user assign other company name, return out of data"
        },
        "index": {
            "type": "string",
            "description": "index arguement means the finacial index that you want to extract from the raw data frame\
                string of index include ['Cost of Goods Sold', 'Operating Expense', 'Operating Income', 'Revenue', 'Tax Expense', 'Total Asset' , 'Gross profit margin' , 'Operating margin']. \
                User can input more than one index. For example, user_query = '我想知道 Apple 在 2023 的 revenue 和 Cost of Goods Sold', you should return like this format ['Revenue' , 'Cost of Goods Sold']\
                So if user give multiple indeces input, return the list of indeces. \
                If user assign other index name, return out of data. \
                如果使用者輸入的是中文，請對應以下的指標名稱 ,['銷貨成本', '營業費用', '營業收入', '營收', '稅費', '總資產', '毛利率', '營業利益率']"
        },
        "start_time": {
            "type": "string",
            "description": "user can assign the start time of the data, the format should be 'year_quarter', for example '2020 Q1' means 2020 Q1, then you should return 2020_1.\
                If user assign 'all' or not assign, return 2020_1. \
                如果使用者輸入的是中文，請對應以下的時間格式，例如'2020 Q1'代表2020年第一季，則你應該回傳2020_1。"
        },
        "end_time": {
            "type": "string",
            "description": "user can assign the end time of the data, the format should be 'year_quarter', for example '2023 Q4' means 2023 Q4, then you should return 2023_4.\
                If user assign 'all' or not assign, return 2024_3. \
                如果使用者輸入的是中文，請對應以下的時間格式，例如'2023 Q4'代表2023年第四季，則你應該回傳2023_4。"
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

plot_tool = Tool(
    function_declarations=[get_plot_args],
)

def parse_time_range(start, end):
    """解析 start_time 和 end_time，回傳所有 (年份, 季度) 的範圍"""
    start_year, start_qtr = map(int, start.split("_"))
    end_year, end_qtr = map(int, end.split("_"))
    
    years_quarters = []
    
    for year in range(start_year, end_year + 1):
        for quarter in range(1, 5):
            if (year == start_year and quarter < start_qtr) or (year == end_year and quarter > end_qtr):
                continue
            years_quarters.append((str(year), f"Q{quarter}"))  # **確保 year 是 str，Qtr 是 "Q1", "Q2" 這類型**

    return years_quarters


def parse_user_query_with_gemini(query):
    model = GenerativeModel("gemini-1.5-pro-001")

    try:
        print(f"User query: {query}") 
        
        response = model.generate_content(
            query,
            tools=[plot_tool],  
            tool_config=ToolConfig(
                function_calling_config=ToolConfig.FunctionCallingConfig(
                    mode=ToolConfig.FunctionCallingConfig.Mode.ANY,
                )
            )
        )
        
        print(f"Raw Gemini response: {response}")

        if not response or not response.candidates:
            print("No functional response from Gemini")
            return None

        candidate = response.candidates[0]

        if not candidate.content.parts:
            print("Gemini response is empty!")
            return None

        response_part = candidate.content.parts[0]

        if hasattr(response_part, "function_call") and response_part.function_call:
            function_call = response_part.function_call
            function_args = function_call.args  
            
            print(f"Extracted arguments: {function_args}")  

            if not function_args:
                print("Function call args is empty！")
                return None

            # **確保 index 是 list**
            if "index" in function_args:
                function_args["index"] = function_args["index"].split(", ") if isinstance(function_args["index"], str) else [function_args["index"]]

            # **確保 start_time 和 end_time 格式為 YYYY_Q**
            def validate_time_format(time_str, default):
                """檢查 YYYY_Q 格式，例如 '2023_3'"""
                parts = time_str.split("_")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    year, quarter = int(parts[0]), int(parts[1])
                    if 1 <= quarter <= 4:
                        return f"{year}_{quarter}"
                print(f"Error: Invalid time format '{time_str}', expected 'YYYY_Q'. Using default: {default}")
                return default

            if "start_time" in function_args:
                function_args["start_time"] = validate_time_format(function_args["start_time"], "2020_1")

            if "end_time" in function_args:
                function_args["end_time"] = validate_time_format(function_args["end_time"], "2024_3")

            # **儲存結果**
            with open("gemini_parsed_output.json", "w", encoding="utf-8") as json_file:
                json.dump(function_args, json_file, indent=4, ensure_ascii=False)

            print("Save parsed result to 'gemini_parsed_output.json'")
            return function_args  

        else:
            print("Cannot find function_call， API form might be wrong！")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None



def plot_financial_data(df, parsed_query):
    if not parsed_query or not isinstance(parsed_query, dict):
        print("Parsed query is empty or invalid, please try again!")
        return
    
    company = parsed_query.get("company", "")
    index = parsed_query.get("index", "")
    start_time = parsed_query.get("start_time", "")
    end_time = parsed_query.get("end_time", "")

    if not company or not index or not start_time or not end_time:
        print("Cannot parse query, please try again!")
        return
    
    company = [company] if isinstance(company, str) else company
    index = [index] if isinstance(index, str) else index
    
    # **確保 time_range 是 list[(YYYY, "QX")]**
    time_range = parse_time_range(start_time, end_time)

    print(f"Company: {company}")
    print(f"Index: {index}")
    print(f"Time range: {time_range}")  

    plt.figure(figsize=(10, 6))

    for idx in index:
        # **篩選數據時，確保年份轉為 str 並匹配季度格式**
        filtered_df = df[
            (df['Company Name'] == company[0]) & 
            (df['Index'] == idx) & 
            df[['CALENDAR_YEAR', 'CALENDAR_QTR']].apply(tuple, axis=1).isin(time_range)
        ].sort_values(by=['CALENDAR_YEAR', 'CALENDAR_QTR'])

        print(f"\nFiltered data for Index: {idx}")
        print(filtered_df)

        if not filtered_df.empty:
            x_labels = [f"{y}_{q}" for y, q in zip(filtered_df['CALENDAR_YEAR'], filtered_df['CALENDAR_QTR'])]
            plt.plot(x_labels, filtered_df['USD_Value'], marker='o', linestyle='-', label=idx)
        else:
            print(f"Warning: No data found for Index {idx}, skipping...")

    plt.xlabel('Year_Quarter')
    plt.ylabel('USD Value')
    plt.title(f'{company[0]} Financial Metrics from {start_time} to {end_time}')
    plt.xticks(rotation=45)
    plt.legend(title="Index")
    plt.grid(True)
    plt.show()