import json
import os
import re
import sqlite3

import pandas as pd
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from application.backend.chatbot.prompts import PRODUCT_QUERY_PROMPT

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
        return str(col).strip().replace("\n", " ").replace(" ", "_").replace("(", "_").replace(")", "_").replace("-",
                                                                                                                 "_")

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
        product_result = pd.read_sql(query, conn)
        result_json = [
            {col: row for col, row in row_data.items() if pd.notna(row)}
            for _, row_data in product_result.iterrows()
        ]
        result_string = json.dumps(result_json, indent=2)
    except Exception as e:
        print(f"Error executing query: {e}")
        result_string = "Error executing the query."
    conn.close()
    return result_string


def generate_sql_query(query, column_mapping, table_name):
    llm = ChatOpenAI(
        model="gpt-4o",
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
            | PRODUCT_QUERY_PROMPT
            | llm
            | StrOutputParser()
    )
    sql_query = sequence.invoke({"question": query})
    sql_query = re.sub(r'^```sql\s*|```$', '', sql_query, flags=re.IGNORECASE | re.MULTILINE)
    sql_query = sql_query.strip()
    return sql_query


def process_user_query(query):
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

    sql_query = generate_sql_query(query, column_mapping, TABLE_NAME)
    sql_query = sql_query.replace('```', '').strip()

    product_result = query_database(DB_PATH, sql_query)
    response = {
        "result": product_result,
        "parameters": column_mapping[:20],
    }
    return json.dumps(response, indent=2)


if __name__ == '__main__':
    user_question = "What are the core, operate Frequent, Operating Temperature and application for the product M032LG8AE?"
    result = process_user_query(user_question)
    print(result) if result else print("No matching data found.")
