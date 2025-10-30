import tkinter as tk
from tkinter import messagebox
import threading
import keyboard
import requests
import time
import pyautogui
import pyperclip

API_URL = "http://127.0.0.1:5000/check"

buffer = ""
last_time = time.time()

def send_to_backend(text):
    try:
        response = requests.post(API_URL, json={"text": text})
        if response.status_code == 200:
            data = response.json()
            return data.get("suggestion"), data.get("explanation")
    except Exception as e:
        print("Error contacting backend:", e)
    return None, None

def show_popup(original, suggestion, explanation):
    """Show a small popup window with Replace / Ignore buttons."""
    popup = tk.Tk()
    popup.title("Grammar Assistant")
    popup.geometry("420x220")
    popup.attributes("-topmost", True)
    popup.resizable(False, False)

    tk.Label(popup, text="Original Text:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10,0))
    tk.Label(popup, text=original, wraplength=400, justify="left").pack(anchor="w", padx=10)

    tk.Label(popup, text="Suggestion:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10,0))
    tk.Label(popup, text=suggestion, fg="green", wraplength=400, justify="left").pack(anchor="w", padx=10)

    tk.Label(popup, text=f"💬 {explanation}", wraplength=400, justify="left", fg="gray").pack(anchor="w", padx=10, pady=(5,10))

    def replace_text():
        pyautogui.hotkey("ctrl", "a")
        pyperclip.copy(suggestion)
        pyautogui.hotkey("ctrl", "v")
        popup.destroy()

    def ignore_text():
        popup.destroy()

    button_frame = tk.Frame(popup)
    button_frame.pack(pady=10)
    tk.Button(button_frame, text="✅ Replace", command=replace_text, bg="green", fg="white", width=12).pack(side="left", padx=10)
    tk.Button(button_frame, text="❌ Ignore", command=ignore_text, bg="red", fg="white", width=12).pack(side="right", padx=10)

    popup.mainloop()

def monitor_keyboard():
    global buffer, last_time
    print("⌨ Grammar assistant running — type anywhere (Notepad, browser, etc).")
    while True:
        try:
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN:
                if event.name == "space":
                    if time.time() - last_time > 1.5 and len(buffer.strip()) > 3:
                        suggestion, explanation = send_to_backend(buffer)
                        if suggestion and suggestion.strip() != buffer.strip():
                            show_popup(buffer.strip(), suggestion.strip(), explanation)
                        buffer = ""
                    else:
                        buffer += " "
                    last_time = time.time()
                elif event.name == "enter":
                    buffer = ""
                elif len(event.name) == 1:
                    buffer += event.name
        except Exception as e:
            print("Keyboard monitoring error:", e)
            time.sleep(1)

def run():
    threading.Thread(target=monitor_keyboard, daemon=True).start()

if __name__ == "__main__":
    run()
