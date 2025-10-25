import sqlite3
import pandas as pd
import os
from typing import Optional

def sqlite_to_excel(db_file: str, excel_file: str, table_name: Optional[str] = None):
    """
    Connects to an SQLite database file, extracts data from a specified table,
    and converts it into an Excel (.xlsx) file.

    Args:
        db_file (str): Path to the input SQLite database file (.db or .sqlite).
        excel_file (str): Path for the output Excel file (.xlsx).
        table_name (str, optional): The name of the table to extract. 
                                    If None, the script will prompt the user.
    """
    if not os.path.exists(db_file):
        print(f"Error: Database file not found at '{db_file}'")
        return

    conn = None
    try:
        # 1. Connect to the SQLite database
        conn = sqlite3.connect(db_file)
        print(f"Successfully connected to database: {db_file}")

        # 2. If table name is not provided, list available tables
        if table_name is None:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                print("Error: No tables found in the database.")
                return

            print("\nAvailable tables:")
            for i, table in enumerate(tables):
                print(f"  {i+1}. {table}")
            
            # Prompt user to select a table
            selection = input("\nEnter the table name (or number) to export: ").strip()
            
            if selection.isdigit() and 1 <= int(selection) <= len(tables):
                table_name = tables[int(selection) - 1]
            elif selection in tables:
                table_name = selection
            else:
                print(f"Error: Invalid selection or table name provided: '{selection}'")
                return

        # 3. Read data from the selected table into a pandas DataFrame
        print(f"\nReading data from table: '{table_name}'...")
        sql_query = f"SELECT * FROM {table_name}"
        
        # pandas automatically handles the SQL connection and query execution
        df = pd.read_sql_query(sql_query, conn)
        
        if df.empty:
             print(f"Warning: Table '{table_name}' is empty. No data to export.")
             return

        print(f"Read {len(df)} rows and {len(df.columns)} columns.")

        # 4. Write the DataFrame to an Excel file
        print(f"Writing data to Excel file: {excel_file}...")
        
        # openpyxl engine is used for .xlsx format, which is required
        df.to_excel(excel_file, sheet_name=table_name, index=False, engine='openpyxl')
        
        print("\n✅ Conversion complete!")
        print(f"Data from table '{table_name}' has been saved to '{excel_file}'.")

    except sqlite3.OperationalError as e:
        print(f"\nDatabase Operational Error (Table/Query Issue): {e}")
    except PermissionError as e:
        # Catch the specific Errno 13 here
        print("\n❌ FILE PERMISSION ERROR (Errno 13)")
        print(f"The script cannot write to '{excel_file}'.")
        print("Please ensure the following:")
        print("1. The Excel file is **CLOSED** completely in all applications (like Excel).")
        print("2. You have write permissions to the directory.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

# --- Example Usage ---
if __name__ == "__main__":
    # --- Configuration ---
    
    # 1. Set the path to your input database file
    INPUT_DB = 'responses.db' 
    
    # 2. Set the path for your output Excel file
    OUTPUT_EXCEL = 'exported_student_data.xlsx'
    
    # 3. Optionally specify the table name. Set to None to prompt the user.
    # If your table is named 'responses', you can use: TABLE_TO_EXPORT = 'responses'
    TABLE_TO_EXPORT = 'responses' 

    # --- Run Conversion ---
    sqlite_to_excel(INPUT_DB, OUTPUT_EXCEL, TABLE_TO_EXPORT)
