import sqlite3
import os
from datetime import datetime, timedelta
import pandas as pd

DB_FILE = "patient_database.db"
CSV_FILE = "people_data.csv"

def create_tables():
    """Create necessary tables in the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create patient info table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_info (
        id INTEGER PRIMARY KEY,
        name TEXT,
        age INTEGER,
        medical_history TEXT,
        last_doctor_visit TEXT,
        next_medication_time TEXT,
        family_members TEXT
    )
    ''')
    
    # Create visit history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visit_history (
        id INTEGER PRIMARY KEY,
        person_name TEXT,
        relation TEXT,
        visit_date TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database tables created successfully.")

def insert_sample_data():
    """Insert sample data into the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if patient data already exists
    cursor.execute("SELECT COUNT(*) FROM patient_info")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Insert patient data
        cursor.execute('''
        INSERT INTO patient_info (name, age, medical_history, last_doctor_visit, next_medication_time, family_members)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ("John Doe", 25, "Diabetes, Hypertension", "2024-02-01", "8:00 AM", "Alice (mother), Bob (father)"))
        print("Patient data inserted.")
    else:
        print("Patient data already exists.")
    
    # Add some sample visit history
    # Get people from CSV
    if os.path.exists(CSV_FILE):
        try:
            people_df = pd.read_csv(CSV_FILE)
            
            # Check if visit history is empty
            cursor.execute("SELECT COUNT(*) FROM visit_history")
            visit_count = cursor.fetchone()[0]
            
            if visit_count == 0:
                # Add some fake visit history
                today = datetime.now()
                
                for i, row in people_df.iterrows():
                    # Random visit in the last week
                    days_ago = i % 7
                    visit_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    cursor.execute('''
                    INSERT INTO visit_history (person_name, relation, visit_date)
                    VALUES (?, ?, ?)
                    ''', (row['Name'], row['Relation'], visit_date))
                
                print(f"Added {len(people_df)} sample visits to history.")
            else:
                print("Visit history already has data.")
                
        except Exception as e:
            print(f"Error loading CSV: {e}")
    else:
        print(f"CSV file {CSV_FILE} not found. No sample visit history added.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Create tables
    create_tables()
    
    # Insert sample data
    insert_sample_data()
    
    print("Database setup complete!")
