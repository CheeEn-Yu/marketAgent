from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerativeModel,
    Part,
    Tool,
)
import csv

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
            "description": "user can assign the start time of the data, the format should be 'year_quarter', for example '2020 Q1' means 2020 Q1, then you should return 2020_Q1.\
                If user assign 'all' or not assign, return 2020_Q1. \
                如果使用者輸入的是中文，請對應以下的時間格式，例如'2020 Q1'代表2020年第一季，則你應該回傳2020_Q1。"
        },
        "end_time": {
            "type": "string",
            "description": "user can assign the end time of the data, the format should be 'year_quarter', for example '2023 Q4' means 2023 Q4, then you should return 2023_Q4.\
                If user assign 'all' or not assign, return 2024_Q3. \
                如果使用者輸入的是中文，請對應以下的時間格式，例如'2023 Q4'代表2023年第四季，則你應該回傳2023_Q4。"
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
