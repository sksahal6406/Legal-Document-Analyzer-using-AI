import webview
import subprocess
import time

def start_django():
    """Start Django server in a separate process."""
    subprocess.Popen(["python", "manage.py", "runserver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)  # Give Django time to start

if __name__ == "__main__":
    start_django()
    webview.create_window("Legal Doc Analyzer", "http://127.0.0.1:8000")
    webview.start()
