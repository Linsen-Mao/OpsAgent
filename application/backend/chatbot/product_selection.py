import json
import os
import pandas as pd
import sqlite3
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILE_PATH = os.path.join(BASE_DIR, "data", "Product_Selection_Guide.xlsx")
DB_PATH = os.path.join(BASE_DIR, "data", "products.db")
SHEET_NAME = "Product Selection Table"
TABLE_NAME = "product_parameters"

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

def load_and_clean_excel(file_path, sheet_name):
    excel_data = pd.ExcelFile(file_path)
    data = excel_data.parse(sheet_name, header=2)

    data = data.dropna(how="all", axis=0).dropna(how="all", axis=1)

    data_start_row = data[data['Product'] == "Part No."].index[0] + 1
    product_data = data.iloc[data_start_row:].reset_index(drop=True)

    def clean_column_name(col):
        return str(col).strip().replace("\n", " ").replace(" ", "_").replace("(", "_").replace(")", "_").replace("-", "_")

    product_data.columns = data.iloc[0].map(clean_column_name)
    product_data = product_data.rename(columns={'Part_No.': 'Part_No'})
    product_data = product_data.dropna(subset=['Part_No'])

    return product_data

def save_to_database(data, db_path, table_name="product_parameters"):
    conn = sqlite3.connect(db_path)
    data.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

def is_database_ready(db_path, table_name):
    if not os.path.exists(db_path):
        return False
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT 1 FROM {table_name} LIMIT 1;"
        conn.execute(query)
        conn.close()
        return True
    except sqlite3.Error:
        return False

def query_database(db_path, query):
    conn = sqlite3.connect(db_path)
    try:
        print(f"Executing SQL Query: {query}")
        result = pd.read_sql(query, conn)
        result_json = [
            {col: row for col, row in row_data.items() if pd.notna(row)}
            for _, row_data in result.iterrows()
        ]
        result_string = json.dumps(result_json, indent=2)
    except Exception as e:
        print(f"Error executing query: {e}")
        result_string = "Error executing the query."
    conn.close()
    return result_string

def generate_sql_query(user_question, column_mapping, table_name):
    prompt = PromptTemplate(
        input_variables=["question", "columns", "table_name"],
        template=(
            "You are a helpful assistant. Generate a valid SQL query based on the user's question.\n"
            "Question: {question}\n"
            "Available columns: {columns}\n"
            "Table name: {table_name}\n"
            "Ensure the query is executable in SQLite and does not include any markdown format.\n"
            "If the user doesn't specify the number of rows to return, return the top 5 rows.\n"
            "If the user asks for more than 10 rows, return only the first 10 rows.\n"
            "Only return the columns that are relevant to the user's question.\n"
            "Return only the SQL query."
        ),
    )
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=openai_api_key,
        streaming=False
    )
    sequence = (
        {
            "question": RunnablePassthrough(),
            "columns": lambda _: ", ".join(column_mapping),
            "table_name": lambda _: table_name,
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    sql_query = sequence.invoke({"question": user_question})
    print(f"Generated SQL Query: {sql_query}")  # Print the SQL query
    return sql_query

def process_user_query(user_question):
    # Check if the database and table are ready
    if not is_database_ready(DB_PATH, TABLE_NAME):
        print("Database or table not found. Regenerating from Excel file.")
        data = load_and_clean_excel(FILE_PATH, SHEET_NAME)
        save_to_database(data, DB_PATH, TABLE_NAME)
    else:
        print("Database and table found. Skipping regeneration.")

    conn = sqlite3.connect(DB_PATH)
    column_mapping = pd.read_sql(f"PRAGMA table_info({TABLE_NAME});", conn)['name'].tolist()
    conn.close()

    sql_query = generate_sql_query(user_question, column_mapping, TABLE_NAME)
    sql_query = sql_query.strip()

    result = query_database(DB_PATH, sql_query)
    response = {
        "result": result,
        "parameters": column_mapping[:60],
    }
    return json.dumps(response, indent=2)

if __name__ == '__main__':
    user_question = "What are the core, operate Frequent and Operating Temperature for the product M032LG8AE?"
    result = process_user_query(user_question)
    print(result) if result else print("No matching data found.")
