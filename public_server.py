from flask import Flask
from app import app
import os
import subprocess
import sys
import webbrowser
from threading import Thread
import time

def install_localtunnel():
    try:
        # Check if npm is installed
        subprocess.run(['npm', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("Error: npm is not installed. Please install Node.js from: https://nodejs.org/")
        sys.exit(1)
    
    # Install localtunnel globally
    subprocess.run(['npm', 'install', '-g', 'localtunnel'])

def start_localtunnel(port):
    process = subprocess.Popen(['lt', '--port', str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Read the URL from the output
    for line in process.stdout:
        if "your url is:" in line.lower():
            url = line.split("is:")[-1].strip()
            print(f"\n{'='*50}")
            print(f"Your app is now available at: {url}")
            print(f"Share this URL with anyone to access your app!")
            print(f"{'='*50}\n")
            
            # Open the URL in the default browser
            webbrowser.open(url)
            break

def run_app():
    app.run(host='0.0.0.0', port=8000, threaded=True)

if __name__ == '__main__':
    print("Setting up public access to your app...")
    
    # Install localtunnel if not already installed
    install_localtunnel()
    
    # Start Flask app in a separate thread
    Thread(target=run_app).start()
    
    # Give Flask a moment to start
    time.sleep(2)
    
    # Start localtunnel
    start_localtunnel(8000) 