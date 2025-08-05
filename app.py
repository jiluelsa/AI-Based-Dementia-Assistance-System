from flask import Flask, render_template, Response, request, jsonify
import cv2
import face_recognition
import pickle
import os
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import ollama  # Import Ollama to call the chatbot
import numpy as np 
import json
import random
import time
import pytz
from tzlocal import get_localzone
from apscheduler.schedulers.background import BackgroundScheduler

# Memory file paths
MEMORY_FOLDER = "memory"
CHAT_MEMORY_FILE = os.path.join(MEMORY_FOLDER, "chat_memory.json")
FACE_MEMORY_FILE = os.path.join(MEMORY_FOLDER, "recognized_faces.json")
DAILY_ROUTINES_FILE = os.path.join(MEMORY_FOLDER, "daily_routines.json")

# Database and other file paths
KNOWN_FACES_DIR = "known_faces"
ENCODINGS_FILE = "face_encodings.pkl"
CSV_FILE = "people_data.csv"
DB_FILE = "patient_database.db"  # SQLite Database

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create reminders table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            due_time DATETIME NOT NULL,
            category TEXT DEFAULT 'general',
            is_completed INTEGER DEFAULT 0,
            is_recurring INTEGER DEFAULT 0,
            recurrence_pattern TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create patient_info table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patient_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            medical_history TEXT,
            last_doctor_visit DATE,
            next_medication_time TIME,
            family_members TEXT
        )
    ''')
    
    # Create known_people table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS known_people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            relation TEXT,
            last_visit DATETIME
        )
    ''')
    
    # Create visit_history table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visit_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_name TEXT NOT NULL,
        visit_date DATETIME NOT NULL
    )
    ''')
    
    # Insert default patient if not exists
    cursor.execute('SELECT id FROM patient_info WHERE id=1')
    if not cursor.fetchone():
        cursor.execute('''
        INSERT INTO patient_info (name, age, medical_history, last_doctor_visit, next_medication_time, family_members)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', ('John Doe', 65, 'Dementia, Hypertension', '2024-02-01', '08:00:00', 'Alice (mother), Bob (father)'))
    
    conn.commit()
    conn.close()

def check_upcoming_reminders():
    """Check for upcoming reminders and return notifications"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get current time
    now = datetime.now()
    # Look for reminders due in the next 30 minutes that haven't been notified in the last 15 minutes
    thirty_mins_future = now + timedelta(minutes=30)
    fifteen_mins_ago = now - timedelta(minutes=15)
    
    cursor.execute('''
    SELECT id, title, description, due_time, category
    FROM reminders
    WHERE due_time BETWEEN ? AND ?
    AND (last_notification IS NULL OR last_notification < ?)
    AND is_completed = 0
    ''', (now.strftime('%Y-%m-%d %H:%M:%S'), 
          thirty_mins_future.strftime('%Y-%m-%d %H:%M:%S'),
          fifteen_mins_ago.strftime('%Y-%m-%d %H:%M:%S')))
    
    upcoming_reminders = cursor.fetchall()
    
    # Update last_notification for found reminders
    for reminder in upcoming_reminders:
        cursor.execute('''
        UPDATE reminders
        SET last_notification = ?
        WHERE id = ?
        ''', (now.strftime('%Y-%m-%d %H:%M:%S'), reminder[0]))
    
    conn.commit()
    conn.close()
    
    return upcoming_reminders

def add_reminder(title, description, due_time, category, is_recurring=False, recurrence_pattern=None):
    """Add a new reminder to the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Ensure description is not None and properly formatted
        description = description.strip() if description else ""
        
        # Debug print
        print(f"Adding reminder with title: {title}")
        print(f"Description: {description}")
        print(f"Due time: {due_time}")
        print(f"Category: {category}")
        
        cursor.execute('''
        INSERT INTO reminders (title, description, due_time, category, is_recurring, recurrence_pattern)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, description, due_time, category, is_recurring, recurrence_pattern))
        
        conn.commit()
        print(f"Successfully added reminder: {title} with description: {description}")
        
        # Verify the reminder was added correctly
        cursor.execute('''
        SELECT title, description, due_time, category 
        FROM reminders 
        WHERE title = ? AND due_time = ?
        ''', (title, due_time))
        added_reminder = cursor.fetchone()
        print(f"Verified added reminder: {added_reminder}")
        
    except Exception as e:
        print(f"Error adding reminder: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def get_todays_reminders(for_tomorrow=False):
    """Get all reminders for today or tomorrow"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get target date
        target_date = (datetime.now() + timedelta(days=1)).date() if for_tomorrow else datetime.now().date()
        
        # Format the date for SQLite
        date_str = target_date.strftime('%Y-%m-%d')
        
        cursor.execute('''
        SELECT title, description, due_time, category
        FROM reminders
        WHERE date(due_time) = ?
        AND is_completed = 0
        ORDER BY due_time
        ''', (date_str,))
        
        reminders = cursor.fetchall()
        return reminders
    except Exception as e:
        print(f"Error in get_todays_reminders: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def add_test_reminder():
    """Add a test reminder to the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Add a test reminder for today
        current_time = datetime.now()
        due_time = current_time.replace(hour=current_time.hour + 1, minute=0, second=0, microsecond=0)
        
        cursor.execute('''
            INSERT INTO reminders (title, description, due_time, category)
            VALUES (?, ?, ?, ?)
        ''', (
            "Test Reminder",
            "This is a test reminder to verify the system is working",
            due_time.strftime("%Y-%m-%d %H:%M:%S"),
            "test"
        ))
        
        conn.commit()
        print("Test reminder added successfully")
    except Exception as e:
        print(f"Error adding test reminder: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# Initialize the database
init_db()
# Remove the add_test_reminder() call
# add_test_reminder()  # Commented out to prevent test reminder creation

# Start reminder checking job (checks every 5 minutes)
scheduler.add_job(check_upcoming_reminders, 'interval', minutes=5)

# Ensure memory folder exists
os.makedirs(MEMORY_FOLDER, exist_ok=True)

def load_memory(file_path):
    """Load memory from a JSON file, handling empty or corrupted files."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else {"memories": [], "is_recording": False}
        except (json.JSONDecodeError, ValueError):
            print(f"⚠️ Warning: Resetting {file_path} (corrupted file)")
            return {"memories": [], "is_recording": False}
    return {"memories": [], "is_recording": False}

def save_memory(file_path, data):
    """Save memory to a JSON file."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

app = Flask(__name__)

# Load the database (CSV) containing people details
if os.path.exists(CSV_FILE):
    people_df = pd.read_csv(CSV_FILE)
    people_df["Name"] = people_df["Name"].str.strip()  # Remove extra spaces
else:
    people_df = pd.DataFrame(columns=["Name", "Relation", "Age", "Medical_History", "Last_Visit", "Notes"])

# Load known faces
if os.path.exists(ENCODINGS_FILE):
    try:
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
            known_encodings, known_names = data.get("encodings", []), data.get("names", [])
            known_names = [name.strip() for name in known_names]  # Ensure names are clean
            print(f"Loaded {len(known_encodings)} encodings.")
            print(f"Known Names: {set(known_names)}")
    except Exception as e:
        print(f"Error loading encodings: {e}")
        known_encodings, known_names = [], []
else:
    known_encodings, known_names = [], []

# Initialize webcam
video_capture = cv2.VideoCapture(0)

recognized_name = "Unknown"  # Global variable to store recognized name

def save_person_visit(name, relation="Unknown"):
    """Save a person's visit in the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Get today's date
    visit_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Check if the person is already in known_people
    cursor.execute("SELECT * FROM known_people WHERE name=?", (name,))
    existing_person = cursor.fetchone()

    if existing_person:
        # Update last visit date
        cursor.execute("UPDATE known_people SET last_visit=? WHERE name=?", (visit_date, name))
    else:
        # Insert new person
        cursor.execute("INSERT INTO known_people (name, relation, last_visit) VALUES (?, ?, ?)", 
                       (name, relation, visit_date))

    # Insert into visit history
    cursor.execute("INSERT INTO visit_history (person_name, visit_date) VALUES (?, ?)", (name, visit_date))

    conn.commit()
    conn.close()

def generate_frames():
    """Capture frames, perform face recognition, and store in memory."""
    global recognized_name

    face_memory = load_memory(FACE_MEMORY_FILE)

    while True:
        success, frame = video_capture.read()
        if not success:
            break

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        recognized_name = "Unknown"
        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            
            if True in matches:
                best_match_index = np.argmin(face_distances)
                recognized_name = known_names[best_match_index].strip()

                # Draw bounding box on the detected face
                top, right, bottom, left = [v * 4 for v in face_location]  # Scale back up
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, recognized_name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Store recognized face in memory
        face_memory["last_seen"] = recognized_name
        save_memory(FACE_MEMORY_FILE, face_memory)

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Render the main interface."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Provide the video feed."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_detected_name')
def get_detected_name():
    """Send the detected name to the frontend."""
    global recognized_name
    return jsonify({"name": recognized_name})

@app.route('/get_details', methods=['POST'])
def get_details():
    data = request.get_json()
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "No name provided!"}), 400

    print(f"🔍 Searching details for: {name}")

    # Check CSV first
    person_details = people_df[people_df["Name"].str.lower() == name.lower()]
    if not person_details.empty:
        details = {
            "Name": person_details.iloc[0]["Name"],
            "Relation": person_details.iloc[0]["Relation"],
            "Age": str(person_details.iloc[0]["Age"]),
            "Medical_History": person_details.iloc[0]["Medical_History"],
            "Last_Visit": person_details.iloc[0]["Last_Visit"],
            "Notes": person_details.iloc[0]["Notes"]
        }
        return jsonify(details)

    # Check database if not found in CSV
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, relation, last_visit FROM known_people WHERE LOWER(name)=?", (name.lower(),))
    db_record = cursor.fetchone()
    conn.close()

    if db_record:
        details = {
            "Name": db_record[0],
            "Relation": db_record[1],
            "Last_Visit": db_record[2]
        }
        return jsonify(details)

    return jsonify({"error": "No details found!"}), 404

@app.route('/check_time')
def check_time():
    """Debug endpoint to check the system time"""
    current_time = datetime.now()
    current_hour = current_time.hour
    
    # Determine greeting based on hour
    if 5 <= current_hour < 12:
        greeting = "Good morning"
    elif 12 <= current_hour < 17:
        greeting = "Good afternoon"
    elif 17 <= current_hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Good night"
    
    return jsonify({
        "server_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "hour": current_hour,
        "greeting": greeting,
        "timezone_info": {
            "timezone": current_time.astimezone().tzinfo.tzname(current_time),
            "utc_offset": current_time.astimezone().utcoffset().total_seconds() / 3600
        }
    })

def load_chat_memory():
    """Load chat memory from file"""
    if os.path.exists(CHAT_MEMORY_FILE):
        try:
            with open(CHAT_MEMORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"memories": [], "is_recording": False}
    return {"memories": [], "is_recording": False}

def save_chat_memory(memory_data):
    """Save chat memory to file"""
    with open(CHAT_MEMORY_FILE, 'w') as f:
        json.dump(memory_data, f, indent=4)

@app.route('/chatbot', methods=['POST'])
def chatbot():
    """Process user message and return a response."""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip().lower()

        # Load chat memory
        chat_memory = load_chat_memory()
        
        # Handle memory commands
        if user_message == "open memory":
            chat_memory["is_recording"] = True
            save_chat_memory(chat_memory)
            return jsonify({"response": "Memory recording started. Write your diary entry. Type 'close memory' when you're done."})
            
        elif user_message == "close memory":
            chat_memory["is_recording"] = False
            save_chat_memory(chat_memory)
            return jsonify({"response": "Memory saved."})
            
        elif user_message == "show memory":
            if not chat_memory["memories"]:
                return jsonify({"response": "No memories saved yet."})
            
            # Format memories with just date and content
            formatted_memories = []
            for memory in chat_memory["memories"]:
                if isinstance(memory, dict):
                    date = memory.get("timestamp", "")
                    content = memory.get("content", [""])[0]
                    formatted_memories.append(f"{date}: {content}")
                else:
                    # For newer entries that are just strings
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    formatted_memories.append(f"{current_time}: {memory}")
            
            memory_list = "\n".join(formatted_memories)
            return jsonify({"response": f"Your memories:\n{memory_list}"})
        
        # If memory is recording, save the message and don't respond
        if chat_memory["is_recording"]:
            if user_message not in ["open memory", "close memory", "show memory"]:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                chat_memory["memories"].append(f"{current_time}: {user_message}")
                save_chat_memory(chat_memory)
                return jsonify({"response": "Entry saved. Continue writing or type 'close memory' when done."})
        
        # Get patient info
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Get basic patient info
        cursor.execute("SELECT name, age, medical_history, last_doctor_visit, next_medication_time, family_members FROM patient_info WHERE id=1")
        patient_info = cursor.fetchone()

        # Initialize patient data with defaults
        patient_name = "Unknown"
        patient_age = None
        patient_medical_history = None
        patient_last_visit = None
        patient_next_med = None
        patient_family = None
        
        if patient_info:
            patient_name = patient_info[0]
            patient_age = patient_info[1]
            patient_medical_history = patient_info[2]
            patient_last_visit = patient_info[3]
            patient_next_med = patient_info[4]
            patient_family = patient_info[5]
        
        # Simple direct matches first
        if user_message in ["hi", "hello", "hey"]:
            current_hour = datetime.now().hour
            greeting = "Good morning" if 5 <= current_hour < 12 else "Good afternoon" if 12 <= current_hour < 17 else "Good evening"
            response = f"{greeting}, {patient_name}! How can I help you today?"
            
            # Save greeting in memory if recording
            if chat_memory["is_recording"]:
                chat_memory["memories"].append(f"Assistant: {response}")
                save_chat_memory(chat_memory)
                
            return jsonify({"response": response})
        
        if user_message in ["tell my name", "what is my name", "who am i"]:
            return jsonify({"response": f"Your name is {patient_name}."})
            
        if "tell" in user_message and "about" in user_message and ("myself" in user_message or "me" in user_message):
            response = f"Your name is {patient_name}. "
            details = []
            if patient_age:
                details.append(f"You are {patient_age} years old")
            if patient_medical_history:
                details.append(f"Your medical history includes {patient_medical_history}")
            if patient_last_visit:
                details.append(f"Your last doctor visit was on {patient_last_visit}")
            if patient_next_med:
                details.append(f"Your next medication is scheduled for {patient_next_med}")
            if patient_family:
                details.append(f"Your family members include {patient_family}")
            if details:
                response += " " + ". ".join(details) + "."
            return jsonify({"response": response})
        
        # Handle reminder requests
        if any(word in user_message for word in ["reminder", "schedule", "todo", "task"]):
            try:
                # Check if user is asking for tomorrow's reminders
                is_tomorrow = any(word in user_message for word in ["tomorrow", "tomorrow's", "next day"])
                
                # Get reminders
                reminders = get_todays_reminders(for_tomorrow=is_tomorrow)
                
                if reminders:
                    day_text = "tomorrow" if is_tomorrow else "today"
                    response = f"Here are your reminders for {day_text}:\n\n"
                    for index, reminder in enumerate(reminders, 1):
                        title, desc, due_time, category = reminder
                        try:
                            # Try parsing with different formats
                            try:
                                time_obj = datetime.strptime(due_time, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                try:
                                    time_obj = datetime.strptime(due_time, "%Y-%m-%dT%H:%M")
                                except ValueError:
                                    print(f"Warning: Could not parse time: {due_time}")
                                    time_obj = datetime.now()
                            
                            time_str = time_obj.strftime("%I:%M %p")
                            response += f"{index}. {title} at {time_str}\n"
                            
                            # Always show description if it exists and is not empty
                            if desc and desc.strip():
                                response += f"   Description: {desc.strip()}\n"
                            
                            # Show category if it's not 'general'
                            if category and category.lower() != 'general':
                                response += f"   Category: {category}\n"
                            
                            response += "\n"  # Add extra line between reminders
                        except Exception as e:
                            print(f"Error formatting reminder time: {e}")
                            response += f"{index}. {title}\n\n"
                    return jsonify({"response": response.strip()})
                else:
                    day_text = "tomorrow" if is_tomorrow else "today"
                    return jsonify({"response": f"You don't have any reminders scheduled for {day_text}."})
            except Exception as e:
                print(f"Error in reminder handling: {str(e)}")
                return jsonify({"response": "I'm having trouble fetching your reminders. Please try again."})
        
        if "daily routine" in user_message or "my routine" in user_message or "schedule" in user_message:
            # Load daily routine from JSON file
            try:
                with open(DAILY_ROUTINES_FILE, "r") as f:
                    routines = json.load(f)
                # Get today's day name
                today = datetime.now().strftime("%A")
                today_routine = routines.get(today)
                if today_routine:
                    response = f"Your routine for today ({today}):\n"
                    for item in today_routine:
                        response += f"- {item['time']}: {item['activity']} - {item['details']}\n"
                    return jsonify({"response": response.strip()})
                else:
                    return jsonify({"response": f"I don't have a routine for {today}."})
            except Exception as e:
                print(f"Error loading daily routine: {e}")
                return jsonify({"response": "I couldn't load your daily routine. Please check the system files."})
        
        if "who is" in user_message and ("camera" in user_message or "front" in user_message):
            global recognized_name
            if recognized_name != "Unknown":
                # Get person details from CSV first
                person_details = people_df[people_df["Name"].str.lower() == recognized_name.lower()]
                if not person_details.empty:
                    details = {
                        "relation": person_details.iloc[0]["Relation"],
                        "age": person_details.iloc[0]["Age"],
                        "notes": person_details.iloc[0]["Notes"]
                    }
                    response = f"I can see {recognized_name} in front of the camera. "
                    if details["relation"]:
                        response += f"They are your {details['relation']}. "
                    if details["notes"]:
                        response += f"{details['notes']}"
                    return jsonify({"response": response.strip()})
                
                # If not in CSV, check database
                cursor.execute("SELECT relation, last_visit FROM known_people WHERE name=?", (recognized_name,))
                person_info = cursor.fetchone()
                if person_info:
                    relation, last_visit = person_info
                    response = f"I can see {recognized_name} in front of the camera."
                    if relation:
                        response += f" They are your {relation}."
                    if last_visit:
                        response += f" Their last visit was on {last_visit}."
                    return jsonify({"response": response})
                return jsonify({"response": f"I can see {recognized_name} in front of the camera."})
            else:
                return jsonify({"response": "I don't recognize anyone in front of the camera right now."})
        
        if "time" in user_message and any(word in user_message for word in ["what", "tell", "current"]):
            current_time = datetime.now().strftime("%I:%M %p")
            return jsonify({"response": f"The current time is {current_time}."})
        
        # For all other queries, use Ollama
        context = f"You are a helpful assistant. Keep responses clear, accurate, and brief."
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": user_message}
        ]
        
        response = ollama.chat(model="mistral", messages=messages)
        response_text = response["message"]["content"]
        
        # Save response in memory if recording
        if chat_memory["is_recording"]:
            chat_memory["memories"].append(f"Assistant: {response_text}")
            save_chat_memory(chat_memory)
        
        return jsonify({"response": response_text})
        
    except Exception as e:
        print(f"Error in chatbot: {e}")
        return jsonify({"response": "I'm having trouble processing your request. Please try again."})
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/get_reminders')
def get_reminders():
    """Get all reminders for today"""
    try:
        reminders = get_todays_reminders()
        formatted_reminders = []
        for reminder in reminders:
            formatted_reminders.append({
                "title": reminder[0],
                "description": reminder[1],
                "due_time": reminder[2],
                "category": reminder[3]
            })
        return jsonify({"reminders": formatted_reminders})
    except Exception as e:
        print(f"Error getting reminders: {e}")
        return jsonify({"error": "Failed to get reminders"}), 500

@app.route('/add_reminder', methods=['POST'])
def create_reminder():
    """Add a new reminder"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        due_time = data.get('due_time')
        category = data.get('category', 'general').strip()
        is_recurring = data.get('is_recurring', False)
        recurrence_pattern = data.get('recurrence_pattern')
        
        if not title or not due_time:
            return jsonify({"error": "Title and due time are required"}), 400
            
        # Debug print
        print(f"Received reminder data:")
        print(f"Title: {title}")
        print(f"Description: {description}")
        print(f"Due time: {due_time}")
        print(f"Category: {category}")
        
        # Format the due_time to ensure consistent format
        try:
            # Try parsing with different formats
            try:
                time_obj = datetime.strptime(due_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    time_obj = datetime.strptime(due_time, "%Y-%m-%dT%H:%M")
                except ValueError:
                    print(f"Warning: Could not parse time: {due_time}")
                    time_obj = datetime.now()
            
            # Convert to consistent format
            due_time = time_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Error formatting time: {e}")
            return jsonify({"error": "Invalid date format"}), 400
        
        # Verify the data before adding
        if not description:
            print("Warning: Empty description received")
        
        add_reminder(title, description, due_time, category, is_recurring, recurrence_pattern)
        
        # Verify the reminder was added correctly
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
        SELECT title, description, due_time, category 
        FROM reminders 
        WHERE title = ? AND due_time = ?
        ''', (title, due_time))
        added_reminder = cursor.fetchone()
        print(f"Verified added reminder in database: {added_reminder}")
        conn.close()
        
        return jsonify({"message": "Reminder added successfully"})
    except Exception as e:
        print(f"Error adding reminder: {e}")
        return jsonify({"error": "Failed to add reminder"}), 500

@app.route('/check_upcoming')
def check_upcoming():
    """Check for upcoming reminders"""
    try:
        upcoming = check_upcoming_reminders()
        formatted_upcoming = []
        for reminder in upcoming:
            formatted_upcoming.append({
                "id": reminder[0],
                "title": reminder[1],
                "description": reminder[2],
                "due_time": reminder[3],
                "category": reminder[4]
            })
        return jsonify({"upcoming_reminders": formatted_upcoming})
    except Exception as e:
        print(f"Error checking upcoming reminders: {e}")
        return jsonify({"error": "Failed to check upcoming reminders"}), 500

@app.route('/mark_complete', methods=['POST'])
def mark_complete():
    """Mark a reminder as completed"""
    try:
        data = request.get_json()
        reminder_id = data.get('id')
        
        if not reminder_id:
            return jsonify({"error": "Reminder ID is required"}), 400
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE reminders SET is_completed = 1 WHERE id = ?', (reminder_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Reminder marked as completed"})
    except Exception as e:
        print(f"Error marking reminder complete: {e}")
        return jsonify({"error": "Failed to mark reminder as complete"}), 500

@app.route('/capture_person', methods=['POST'])
def capture_person():
    try:
        # Get the current frame from the video feed
        ret, frame = video_capture.read()
        if not ret:
            return jsonify({'success': False, 'error': 'Failed to capture image'})

        # Create a directory for temporary captures if it doesn't exist
        if not os.path.exists('temp_captures'):
            os.makedirs('temp_captures')

        # Save the captured image with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_path = f'temp_captures/capture_{timestamp}.jpg'
        cv2.imwrite(image_path, frame)

        return jsonify({'success': True, 'image_path': image_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_person', methods=['POST'])
def add_person():
    """Add a new person with their details and face encoding."""
    try:
        # Get and validate request data
        data = request.get_json()
        print(f"Received data: {data}")  # Debug print
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400

        # Validate required fields
        if 'image_path' not in data:
            return jsonify({'success': False, 'error': 'Image path is required'}), 400
        if 'name' not in data or not data['name'].strip():
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        image_path = data['image_path']
        name = data['name'].strip()

        print(f"Processing person: {name}, Image: {image_path}")  # Debug print
        
        # Validate image path exists
        if not os.path.exists(image_path):
            return jsonify({'success': False, 'error': f'Image not found at: {image_path}'}), 404

        # Create known_faces directory if it doesn't exist
        os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

        # Move the image to known_faces directory
        new_image_path = os.path.join(KNOWN_FACES_DIR, f"{name}.jpg")
        if os.path.exists(new_image_path):
            os.remove(new_image_path)  # Remove if exists
        os.rename(image_path, new_image_path)
        print(f"Moved image to: {new_image_path}")  # Debug print

        try:
            # Load and encode the face
            image = face_recognition.load_image_file(new_image_path)
            # Convert BGR to RGB if needed
            if len(image.shape) == 3 and image.shape[2] == 3:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = image
            
            # Detect face locations first
            face_locations = face_recognition.face_locations(rgb_image)
            if not face_locations:
                if os.path.exists(new_image_path):
                    os.remove(new_image_path)
                return jsonify({'success': False, 'error': 'No face detected in the image. Please try capturing again.'}), 400
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            if not face_encodings:
                if os.path.exists(new_image_path):
                    os.remove(new_image_path)
                return jsonify({'success': False, 'error': 'Could not encode the face. Please try capturing again.'}), 400
            
            print("Face detected and encoded successfully")  # Debug print
            
            # Update face encodings
            global known_encodings, known_names
            
            # Remove existing encodings for this person if they exist
            if name in known_names:
                indices = [i for i, n in enumerate(known_names) if n == name]
                for index in sorted(indices, reverse=True):
                    known_names.pop(index)
                    known_encodings.pop(index)
            
            known_encodings.append(face_encodings[0])
            known_names.append(name)
            
            # Save updated encodings
            try:
                with open(ENCODINGS_FILE, 'wb') as f:
                    pickle.dump({
                        "encodings": known_encodings,
                        "names": known_names
                    }, f)
                print("Face encodings saved successfully")  # Debug print
            except Exception as e:
                print(f"Error saving encodings: {e}")
                raise

            # Update CSV file
            try:
                if os.path.exists(CSV_FILE):
                    people_df = pd.read_csv(CSV_FILE)
                else:
                    people_df = pd.DataFrame(columns=["Name", "Relation", "Age", "Medical_History", "Last_Visit", "Notes"])
                
                # Add new person to DataFrame
                new_person = pd.DataFrame([{
                    "Name": name,
                    "Relation": data.get('relation', ''),
                    "Age": data.get('age', ''),
                    "Medical_History": data.get('medical_history', ''),
                    "Last_Visit": datetime.now().strftime('%Y-%m-%d'),
                    "Notes": data.get('notes', '')
                }])
                
                # Remove existing entry if exists
                people_df = people_df[people_df["Name"].str.lower() != name.lower()]
                people_df = pd.concat([people_df, new_person], ignore_index=True)
                people_df.to_csv(CSV_FILE, index=False)
                print("CSV file updated successfully")  # Debug print
            except Exception as e:
                print(f"Warning - CSV update failed: {e}")
                # Continue even if CSV update fails

            # Update database
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()

                # Remove existing entry if exists
                cursor.execute("DELETE FROM known_people WHERE LOWER(name)=?", (name.lower(),))
                
                # Insert new entry
                cursor.execute('''
                    INSERT INTO known_people (name, relation, last_visit)
                    VALUES (?, ?, ?)
                ''', (
                    name, 
                    data.get('relation', 'Unknown'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                conn.commit()
                print("Database updated successfully")  # Debug print
            except Exception as e:
                print(f"Error updating database: {e}")
                raise
            finally:
                if 'conn' in locals():
                    conn.close()

            return jsonify({
                'success': True,
                'message': f'Successfully added {name} to known faces'
            })
            
        except Exception as e:
            # If there was an error during processing, clean up
            if os.path.exists(new_image_path):
                os.remove(new_image_path)
            print(f"Error processing image: {str(e)}")  # Debug print
            raise

    except Exception as e:
        error_msg = str(e)
        print(f"Error adding person: {error_msg}")  # Debug print
        return jsonify({
            'success': False,
            'error': f'Failed to save person details: {error_msg}'
        }), 500

@app.route('/debug/db', methods=['GET'])
def debug_db():
    """Debug endpoint to check database structure"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        result = {"tables": []}
        
        # For each table, get its structure and sample data
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            sample_data = cursor.fetchall()
            
            result["tables"].append({
                "name": table_name,
                "columns": columns,
                "sample_data": sample_data
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if 'conn' in locals():
            conn.close()

def ensure_reminders_table():
    """Ensure the reminders table exists with the correct structure"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create reminders table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            due_time DATETIME NOT NULL,
            category TEXT DEFAULT 'general',
            is_completed INTEGER DEFAULT 0,
            is_recurring INTEGER DEFAULT 0,
            recurrence_pattern TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_notification DATETIME
        )
        ''')
        
        conn.commit()
        print("Reminders table verified")
    except Exception as e:
        print(f"Error ensuring reminders table: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def clear_reminders():
    """Clear all existing reminders from the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders")
        conn.commit()
        print("All reminders cleared from database")
    except Exception as e:
        print(f"Error clearing reminders: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

# Call these functions during initialization
ensure_reminders_table()
# Remove the clear_reminders() call to prevent clearing existing reminders
# clear_reminders()  # Commented out to prevent clearing reminders on startup

# Remove the initialize_sample_reminders() call
# initialize_sample_reminders()  # Commented out to prevent sample reminder creation

@app.route('/debug/reminders', methods=['GET'])
def debug_reminders():
    """Debug endpoint to check reminders table content"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute("PRAGMA table_info(reminders)")
        columns = cursor.fetchall()
        
        # Get all reminders
        cursor.execute("SELECT * FROM reminders")
        reminders = cursor.fetchall()
        
        result = {
            "table_structure": columns,
            "reminders": reminders
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if 'conn' in locals():
            conn.close()

def check_current_reminders():
    """Check and print all current reminders in the database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT title, description, due_time, category 
        FROM reminders 
        WHERE is_completed = 0
        ORDER BY due_time
        ''')
        reminders = cursor.fetchall()
        return reminders
    except Exception as e:
        print(f"Error checking reminders: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

# Call this function during initialization
check_current_reminders()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True, threaded=True)
