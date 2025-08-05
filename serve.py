from waitress import serve
from app import app
import socket

def get_local_ip():
    """Get the local IP address"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == '__main__':
    host = get_local_ip()
    port = 8080
    print(f"Starting Dementia Assistance System...")
    print(f"Access your app on other devices using:")
    print(f"http://{host}:{port}")
    print("For mobile devices, make sure they are on the same WiFi network.")
    serve(app, host=host, port=port) 