from test_DP_functions import (
    load_and_categorize,
    parse_user_query_with_gemini,
    plot_financial_data
)
import json

file_path = "FIN_Data.csv" 
df, categories = load_and_categorize(file_path)

#分類
print("分類:")
for key, values in categories.items():
    print(f"{key}: {list(values)}")

user_query = input("Please enter your question: ")
parsed_query = parse_user_query_with_gemini(user_query)

# if parsed_query:
#     plot_financial_data(df, parsed_query)
    
#     print("Gemini parsed query:")
#     print(json.dumps(parsed_query, indent=4, ensure_ascii=False))
    
if parsed_query:
    print("Gemini parsed query:")
    #print(json.dumps(parsed_query, indent=4, ensure_ascii=False))

    # plot
    plot_financial_data(df, parsed_query)
else:
    print("Error : Failed to parse query")