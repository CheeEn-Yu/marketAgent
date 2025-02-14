import os
from typing import Dict, List, TypedDict, Annotated
from datetime import datetime
from langgraph.graph import Graph, StateGraph
from langchain_google_vertexai import VertexAI
from langgraph.prebuilt import ToolExecutor
import pandas as pd
import matplotlib.pyplot as plt
from vertexai.generative_models import GenerationConfig, GenerativeModel
import json
import seaborn as sns
import datetime

now = datetime.datetime.now()

# 若要以指定格式輸出，例如 "YYYY-MM-DD HH:MM:SS"
formatted_time = now.strftime("%Y%m%d-%H-%M-%S")

REPORT_DIR = f"summarize_reports/{formatted_time}"
os.makedirs(REPORT_DIR, exist_ok=True)

# 假設 VertexAI、GenerationConfig、Graph、StateGraph 等工具已正確引入
# 以下為示例，請確保實際使用時這些工具正確導入

class AnalysisState(TypedDict):
    csv_path: str
    transcript_path: str
    company: str
    year: int
    quarter: int
    data_analysis: Dict | None
    transcript_analysis: Dict | None
    visualizations: List[Dict] | None
    report_path: str | None

class ReportGeneratorAgent:
    def __init__(self):
        self.model = VertexAI(model_name="gemini-1.5-pro")
        self.tools = self._create_tools()
        self.graph = self._create_graph()
    
    def _create_tools(self):
        return {
            "analyze_data": self._analyze_csv_data,
            "analyze_transcript": self._analyze_transcript,
            "create_visualization": self._create_visualization,
            "generate_report": self._generate_final_report,
            "self_evaluation": self._self_evaluation  # 新增自我評估工具
        }
    
    def _analyze_csv_data(self, state: AnalysisState) -> AnalysisState:
        """分析 CSV 數據，僅使用指定 Company 且年份小於傳入 Year，或年份等於傳入 Year 且 Quarter 小於等於傳入的資料"""
        df = pd.read_csv(state["csv_path"])
        # 過濾 Company
        df = df[df["Company Name"] == state["company"]]
        # 確保 CALENDAR_YEAR 為整數
        df["CALENDAR_YEAR"] = df["CALENDAR_YEAR"].astype(int)
        # 將 CALENDAR_QTR 轉換為整數（假設其格式中包含數字）
        df["CALENDAR_QTR"] = df["CALENDAR_QTR"].str.extract('(\d+)').astype(int)
        # 過濾條件：若 CALENDAR_YEAR 小於傳入的 Year，則保留所有；若等於，則保留 Quarter <= 傳入的 Quarter
        df = df[
            (df["CALENDAR_YEAR"] < state["year"]) |
            ((df["CALENDAR_YEAR"] == state["year"]) & (df["CALENDAR_QTR"] <= state["quarter"]))
        ]
        # 新增 "Period" 欄位作為時間標籤 (例如 "2020 Q1")
        df["Period"] = df["CALENDAR_YEAR"].astype(str) + " Q" + df["CALENDAR_QTR"].astype(str)
        df = df.sort_values(by=["CALENDAR_YEAR", "CALENDAR_QTR"])
        
        # 基本統計分析
        analysis = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numerical_columns": df.select_dtypes(include=['float64', 'int64']).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=['object']).columns.tolist(),
            "basic_stats": df.describe().to_dict()
        }
        state["data_analysis"] = analysis
        # 將處理後的 DataFrame 存入 state 中，以便後續視覺化使用（可選）
        state["data_analysis"]["filtered_df"] = df.to_dict(orient="list")
        return state
    
    def _analyze_transcript(self, state: AnalysisState) -> AnalysisState:
        """分析逐字稿內容"""
        with open(state["transcript_path"], "r", encoding="utf-8") as f:
            transcript = f.read()
        
        prompt = f"""
        You are a financial analyst with expertise in corporate earnings reports, market trends, and financial data interpretation. Your task is to analyze the following transcript and extract key insights to assist in generating a high-quality financial report.

        Please analyze the following transcript and provide:
        1. Company Overview  
           - Company name if mentioned  
           - Industry sector if mentioned  
           - Stock ticker symbol if mentioned  
           - Target stock price if provided  
           - Latest market price if provided  
           - Buy/Hold/Sell recommendation if available  

        2. Financial Performance  
           - Latest revenue figure and YoY/QoQ comparison if available  
           - Latest EPS figure and trends if mentioned  
           - Gross margin or other profitability metrics if available  

        3. Market Trends  
           - Summary of economic, industry, and competitive trends mentioned in the call  

        4. Forward Guidance  
           - Key management outlook, strategic goals, and projected financial performance  

        5. Risk Factors  
           - Major risks or challenges mentioned, such as supply chain, economic downturns, or regulatory issues  

        6. ESG Analysis  
           - Key ESG (Environmental, Social, Governance) initiatives if discussed  

        7. Investment Sentiment  
           - Investor reactions, analyst recommendations, or market response if available  

        8. Notable Quotes  
           - Key statements or direct quotes from executives during the earnings call  

        Transcript:  
        {transcript}  

        Please return the analysis in JSON format.
        """
        response_schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "topic": {
                        "type": "STRING",
                        "description": "Main subject or section from the earnings call"
                    },
                    "critical_point": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "summary": {
                                    "type": "STRING",
                                    "description": "Key takeaway or insight from this topic"
                                },
                                "data": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "STRING",
                                        "description": "Relevant financial figures, trends, or direct quotes"
                                    }
                                }
                            },
                            "required": ["summary", "data"]
                        },
                        "description": "A list of key insights, including financial metrics, market trends, and management outlook"
                    }
                },
                "required": ["topic", "critical_point"]
            }
        }
        
        response = self.model.client.generate_content(
            prompt,
            generation_config=GenerationConfig(
                response_mime_type="application/json", response_schema=response_schema
            ),
        )
        analysis = json.loads(response.text)
        state["transcript_analysis"] = analysis
        return state
        
    def _create_visualization(self, state: AnalysisState) -> AnalysisState:
        """根據數據創建視覺化圖表與表格，展示多季財務數據的趨勢、結構與財務比率。
        當可用季度資料少於 3 筆時，不生成趨勢圖與成長率圖表。"""
        # print("Starting visualization creation...")
        df = pd.read_csv(state["csv_path"])
        # print("CSV data loaded.")
        
        # 確保 CALENDAR_YEAR 和 CALENDAR_QTR 為整數
        df["CALENDAR_YEAR"] = df["CALENDAR_YEAR"].astype(int)
        df["CALENDAR_QTR"] = df["CALENDAR_QTR"].str.extract('(\d+)').astype(int)
        # print("CALENDAR_YEAR and CALENDAR_QTR converted to integers.")
        
        # 過濾指定公司
        df = df[df["Company Name"] == state["company"]]
        # print(f"Filtered data for company: {state['company']}")
        
        # 過濾條件：若 CALENDAR_YEAR 小於傳入的 Year，則保留所有；若等於，則保留 Quarter <= 傳入的 Quarter
        df = df[
            (df["CALENDAR_YEAR"] < state["year"]) |
            ((df["CALENDAR_YEAR"] == state["year"]) & (df["CALENDAR_QTR"] <= state["quarter"]))
        ]
        # print(f"Filtered data for year <= {state['year']} and quarter <= {state['quarter']}")
        
        # 新增 "Period" 欄位 (例如 "2020 Q1")
        df["Period"] = df["CALENDAR_YEAR"].astype(str) + " Q" + df["CALENDAR_QTR"].astype(str)
        df = df.sort_values(by=["CALENDAR_YEAR", "CALENDAR_QTR"])
        # print("Added and sorted by Period column.")
        
        # 透視數據，使 Index 列中的屬性成為單獨的列
        df_pivot = df.pivot_table(index=["Period", "CALENDAR_YEAR", "CALENDAR_QTR"], columns="Index", values="USD_Value").reset_index()
        # print("Pivoted data:")
        # print(df_pivot.head())
        
        visualizations = []
        n = len(df_pivot)  # 可用資料筆數
        # print(f"Number of available data points: {n}")
        
        # 1. 趨勢圖：Revenue 與 Operating Income 趨勢圖（僅當資料筆數>=3時生成）
        if n >= 3 and set(["Revenue", "Operating Income"]).issubset(df_pivot.columns):
            # print("Creating trend visualization...")
            plt.figure(figsize=(10,6))
            plt.plot(df_pivot["Period"], df_pivot["Revenue"], marker="o", label="Revenue")
            plt.plot(df_pivot["Period"], df_pivot["Operating Income"], marker="o", label="Operating Income")
            plt.xlabel("Period")
            plt.ylabel("Amount (Million USD)")
            plt.title(f"{state['company']} Revenue & Operating Income Trend")
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()
            fig_path1 = os.path.join(REPORT_DIR, f"visualization_{len(visualizations)}.png")
            plt.savefig(fig_path1)
            plt.close()
            visualizations.append({
                "type": "trend",
                "path": fig_path1,
                "description": "Revenue & Operating Income Trend"
            })
            # print(f"Trend visualization saved at {fig_path1}")
        
        # 2. 群組長條圖：各季度成本結構 (Revenue, COGS, Operating Expense, Operating Income, Tax Expense)
        # print("Creating bar chart visualization...")
        required_cols = ["Revenue", "Cost of Goods Sold", "Operating Expense", "Operating Income", "Tax Expense"]
        if set(required_cols).issubset(df_pivot.columns):
            periods = df_pivot["Period"]
            bar_width = 0.15
            index = range(len(periods))
            plt.figure(figsize=(12,6))
            plt.bar([i - 2*bar_width for i in index], df_pivot["Revenue"], width=bar_width, label="Revenue")
            plt.bar([i - bar_width for i in index], df_pivot["Cost of Goods Sold"], width=bar_width, label="COGS")
            plt.bar(index, df_pivot["Operating Expense"], width=bar_width, label="Operating Expense")
            plt.bar([i + bar_width for i in index], df_pivot["Operating Income"], width=bar_width, label="Operating Income")
            plt.bar([i + 2*bar_width for i in index], df_pivot["Tax Expense"], width=bar_width, label="Tax Expense")
            plt.xlabel("Period")
            plt.xticks(index, periods, rotation=45)
            plt.ylabel("Amount (Million USD)")
            plt.title(f"{state['company']} Cost Structure by Period")
            plt.legend()
            plt.tight_layout()
            fig_path2 = os.path.join(REPORT_DIR, f"visualization_{len(visualizations)}.png")
            plt.savefig(fig_path2)
            plt.close()
            visualizations.append({
                "type": "bar",
                "path": fig_path2,
                "description": "Cost Structure per Quarter"
            })
            # print(f"Bar chart visualization saved at {fig_path2}")
        
        # 3. 財務比率表：計算毛利率、營業利益率、簡易淨利率，並以表格呈現
        # print("Creating financial ratios table visualization...")
        if set(["Revenue", "Cost of Goods Sold", "Operating Income", "Tax Expense"]).issubset(df_pivot.columns):
            df_pivot["Gross Profit"] = df_pivot["Revenue"] - df_pivot["Cost of Goods Sold"]
            df_pivot["Gross Margin"] = df_pivot["Gross Profit"] / df_pivot["Revenue"]
            df_pivot["Operating Margin"] = df_pivot["Operating Income"] / df_pivot["Revenue"]
            df_pivot["Approx Net Income"] = df_pivot["Operating Income"] - df_pivot["Tax Expense"]
            df_pivot["Net Margin"] = df_pivot["Approx Net Income"] / df_pivot["Revenue"]
            ratio_table = df_pivot[["Period", "Gross Margin", "Operating Margin", "Net Margin"]]
            fig, ax = plt.subplots(figsize=(8, len(ratio_table)*0.5 + 1))
            ax.axis('tight')
            ax.axis('off')
            table = ax.table(cellText=ratio_table.round(2).values,
                             colLabels=ratio_table.columns,
                             cellLoc='center', loc='center')
            plt.title(f"{state['company']} Financial Ratios")
            fig.tight_layout()
            fig_path3 = os.path.join(REPORT_DIR, f"visualization_{len(visualizations)}.png")
            plt.savefig(fig_path3)
            plt.close()
            visualizations.append({
                "type": "table",
                "path": fig_path3,
                "description": "Financial Ratios Table"
            })
            # print(f"Financial ratios table visualization saved at {fig_path3}")
        
        # 4. 成長率趨勢圖：計算 Revenue 與 Operating Income 的環比成長率（僅當資料筆數>=3時生成）
        if n >= 3 and set(["Revenue", "Operating Income"]).issubset(df_pivot.columns):
            # print("Creating growth rate visualization...")
            df_pivot = df_pivot.sort_values(by=["CALENDAR_YEAR", "CALENDAR_QTR"])
            df_pivot["Revenue Growth Rate"] = df_pivot["Revenue"].pct_change() * 100
            df_pivot["Operating Income Growth Rate"] = df_pivot["Operating Income"].pct_change() * 100
            
            plt.figure(figsize=(10, 6))
            plt.plot(df_pivot["Period"], df_pivot["Revenue Growth Rate"], marker='o', label="Revenue Growth Rate")
            plt.plot(df_pivot["Period"], df_pivot["Operating Income Growth Rate"], marker='o', label="Operating Income Growth Rate")
            plt.title(f"{state['company']} Growth Rates")
            plt.xlabel("Period")
            plt.ylabel("Growth Rate (%)")
            plt.legend()
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            fig_path4 = os.path.join(REPORT_DIR, f"visualization_{len(visualizations)}.png")
            plt.savefig(fig_path4)
            plt.close()
            visualizations.append({
                "type": "growth",
                "path": fig_path4,
                "description": "Revenue and Operating Income Growth Rate"
            })
            # print(f"Growth rate visualization saved at {fig_path4}")
        
        state["visualizations"] = visualizations
        # print("Visualization creation completed.")
        return state
    
    def _generate_final_report(self, state: AnalysisState) -> AnalysisState:
        """生成最終報告"""
        prompt = f"""
        Please generate a comprehensive analysis report based on the following information:

        1. Data Analysis Results:
        {json.dumps(state["data_analysis"], indent=2, ensure_ascii=False)}

        2. Transcript Analysis:
        {json.dumps(state["transcript_analysis"], indent=2, ensure_ascii=False)}

        3. Generated Visualizations:
        {json.dumps(state["visualizations"], indent=2, ensure_ascii=False)}

        Please generate a well-structured report in English, including:
        - Executive Summary
        - Key Findings from Data Analysis
        - Highlights from Transcript Analysis
        - Conclusions and Recommendations

        Format Requirement: Markdown Format
        """
        report = self.model.predict(prompt)
        
        # 保存報告
        report_path = os.path.join(REPORT_DIR, "report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        state["report_path"] = report_path
        return state
    
    def _self_evaluation(self, state: AnalysisState) -> AnalysisState:
        """
        自我評估步驟：請模型評估生成的報告內容，檢查是否存在 hallucination 或不一致之處，
        如有必要請提供修正並返回最終修正報告。
        """
        # 讀取已生成的報告內容
        with open(state["report_path"], "r", encoding="utf-8") as f:
            report_content = f.read()
        
        evaluation_prompt = f"""
        You are an expert financial analyst. Please evaluate the following analysis report for any potential hallucinations, inaccuracies, or inconsistencies.
        If you find any issues, please provide corrections along with a brief explanation of the changes made.
        
        Report:
        {report_content}
        """
        evaluated_report = self.model.predict(evaluation_prompt)
        
        # 保存最終經過自我評估修正的報告
        final_report_path = os.path.join(REPORT_DIR, "final_report.md")
        with open(final_report_path, "w", encoding="utf-8") as f:
            f.write(evaluated_report)
        
        state["report_path"] = final_report_path
        return state
    
    def _create_graph(self) -> Graph:
        """創建工作流程圖"""
        workflow = StateGraph(state_schema=AnalysisState)
        
        workflow.add_node("analyze_data", self._analyze_csv_data)
        workflow.add_node("analyze_transcript", self._analyze_transcript)
        workflow.add_node("create_visualization", self._create_visualization)
        workflow.add_node("generate_report", self._generate_final_report)
        workflow.add_node("self_evaluation", self._self_evaluation)  # 新增自我評估節點
        
        workflow.set_entry_point("analyze_data")
        workflow.add_edge("analyze_data", "analyze_transcript")
        workflow.add_edge("analyze_transcript", "create_visualization")
        workflow.add_edge("create_visualization", "generate_report")
        workflow.add_edge("generate_report", "self_evaluation")  # 從生成報告到自我評估
        
        return workflow.compile()
    
    def generate_report(self, csv_path: str, transcript_path: str, company: str, quarter: int, year: int) -> str:
        """執行報告生成流程"""
        initial_state: AnalysisState = {
            "csv_path": csv_path,
            "transcript_path": transcript_path,
            "company": company,
            "year": year,
            "quarter": quarter,
            "data_analysis": None,
            "transcript_analysis": None,
            "visualizations": None,
            "report_path": None
        }
        
        final_state = self.graph.invoke(initial_state)
        return final_state["report_path"]


agent = ReportGeneratorAgent()
report_path = agent.generate_report(
    csv_path="/Users/wei-chinwang/NTU/TSMC_hack/marketAgent/FIN_Data.csv",
    transcript_path="/Users/wei-chinwang/NTU/TSMC_hack/resource/Transcript File/Apple Inc. (NASDAQ AAPL) Q2 2022 Earnings Conference Call.txt",
    company="Apple",
    quarter=2,
    year=2022
)
print(f"Report generated at: {report_path}")