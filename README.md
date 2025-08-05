AI-Based Dementia Assistance System
===================================


Overview:


This is an AI-based support system designed to assist dementia patients with memory-related challenges in daily life. It combines facial recognition, a smart chatbot, a memory journal, and a reminder system to help patients identify people around them, recall personal information, manage their schedule, and communicate more easily.


Features:


1. Face Recognition:
   - A camera module is used to recognize individuals in front of the patient.
   - Matches live face data with pre-stored encodings in the 'known_faces' directory.
   - Displays the identified person's name on the screen.
   - Includes a "More Details" button that shows further information such as:
     - Age
     - Relationship with the patient
     - Shared history (e.g., college, work, etc.)


2. Recognizing New People:
   - When a new person appears, their face is stored in the `unknown_faces/` folder.
   - Near the reminder section, there's a button to capture and register this new face.
   - The user can then add details like name, relationship, etc.
   - Once saved, this person is added to the known_faces list and will be recognized in the future.
   - The system also tracks last seen date/time for recognized individuals.


3. Chatbot (AI-based using Ollama Mistral):
   - Patients can ask:
     - "What is my daily routine?"
     - "Do I have any tasks today?"
     - "What is my name?"
     - "Who am I seeing now?"
   - The chatbot uses a stored dataset and Ollama Mistral model to provide real-time responses.
   - Can answer basic real-world questions like current time, weather, etc.


4. Memory Journal:
   - Patient can interact with a "diary" using commands:
     - "Open memory" – Starts writing a new memory
     - "Close memory" – Ends current memory entry
     - "Show memory" – Displays previously saved entries with date and time


5. Reminder System:
   - Patient can add reminders (e.g., doctor appointment at 4 PM).
   - The system will pop up with the reminder when it's time.
   - Chatbot can list all current reminders upon request.


Technologies Used:
- Python (Flask Framework)
- OpenCV for image capture and processing
- face_recognition library for facial recognition
- Ollama Mistral model for chatbot interaction
- SQLite/CSV file for reminder and memory storage
- HTML/CSS/JavaScript for user interface (via templates)


Project Structure:
- known_faces/        : Folder for storing faces of known individuals (currently empty)
- unknown_faces/      : Stores unknown faces (cleaned for privacy)
- memory/             : Stores diary/memory entries
- templates/          : HTML templates for UI
- screenshots/        : Contains sample screenshots from testing
- chatbot.py          : Chatbot handling logic
- app.py              : Main Flask app
- server.py           : Manages camera and face recognition
- database_setup.py   : Handles database setup and tables
- requirements.txt    : Lists all required Python packages


Important Notes:
- All personal files (including real images, Excel sheets, and face encodings) have been removed for privacy.
- The file `face_encoding.pkl` has been deleted. If you want to test face recognition, please run your own encoding script to generate this file with new faces.
- Reminder and memory data are stored in local files (e.g., CSV or DB) that can be reinitialized with test data.
- Download Face Recognition Models:
Due to GitHub’s file size limit, the `face_recognition_models` folder is uploaded separately as a ZIP file.
[Download face_recognition_models.zip from Google Drive](https://drive.google.com/file/d/1rzMxyZ75dkSfHxO1AFWkmOwE9ZZjnWU-/view?usp=sharing)
After downloading, extract it into the project directory to run the full application.


Demo Screenshots:
You can find sample screenshots of the system during testing in the `screenshots/` folder.


The screenshots include:
- Face recognition in action
- Chatbot answering patient queries
- Reminder system popup
- Capture and save unknown person feature


The files are named:
  Dementia-1.png
  Dementia-2.png
  Dementia-3.png
  Dementia-4.png


Note: The person shown in the screenshots is the author of the project.


How to Run:
1. Install required Python packages:
   pip install -r requirements.txt


2. Run the server:
   python run_server.py


3. Open your browser and go to:
   http://localhost:5000


4. Use the chatbot, face recognition, and memory features through the interface.


Credits:
This project was developed as part of a college academic project on AI and Healthcare Systems.


Author:
Jilu Elsa Jacob  
Saintgits College of Applied Sciences


License:

This project is free to use for academic and non-commercial purposes. Contributions and suggestions are welcome.
