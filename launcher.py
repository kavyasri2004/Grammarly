import threading
import time
import importlib

#  Preload critical modules before starting threads
importlib.import_module("requests")
importlib.import_module("tkinter")
importlib.import_module("pyautogui")
importlib.import_module("pyperclip")

def start_backend():
    try:
        from backend import app as backend_app
        backend_app.run_server(host="127.0.0.1", port=5000)
    except Exception as e:
        print(f"Failed to start backend: {e}")

def start_frontend():
    from frontend import main as frontend_main
    frontend_main.run()

if __name__ == "__main__":
    # Run backend in background thread
    threading.Thread(target=start_backend, daemon=True).start()
    time.sleep(2)  # give backend time to start
    start_frontend()
