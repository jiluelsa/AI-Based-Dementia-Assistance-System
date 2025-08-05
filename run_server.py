import http.server
import socketserver
import socket
import webbrowser
from threading import Thread
import time

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# Get your local IP address
local_ip = get_ip()
PORT = 8000

Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(("", PORT), Handler)

print(f"\n{'='*50}")
print(f"Access your app from other devices using these URLs:")
print(f"{'='*50}")
print(f"\nOn your computer:")
print(f"http://localhost:{PORT}")
print(f"\nOn other devices (phones, tablets, etc.):")
print(f"http://{local_ip}:{PORT}")
print(f"\n{'='*50}")
print("\nMake sure all devices are on the same WiFi network!")
print("Press Ctrl+C to stop the server.")
print(f"{'='*50}\n")

# Open the URL in the default browser after a short delay
def open_browser():
    time.sleep(1.5)
    webbrowser.open(f'http://localhost:{PORT}')

Thread(target=open_browser).start()

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nShutting down the server...")
    httpd.server_close() 