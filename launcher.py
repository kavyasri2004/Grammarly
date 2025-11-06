import keyboard
import threading
import requests
import time
import tkinter as tk
import pyautogui
import pyperclip
import pygetwindow as gw  # NEW: to detect active window


# ---------------------- API FUNCTION ---------------------- #
def get_api_key():
    """Return the full API key (endpoint URL)."""
    return "http://127.0.0.1:5000/check"   #  change this to your deployed API endpoint later


buffer = ""
last_time = time.time()
latest_suggestion = None
latest_original = None
popup = None
capture_enabled = True  # pause listening during replace
last_window = None      #  Track current window


# ---------------------- Utility: Active Window ---------------------- #
def get_active_window_title():
    """Return title of current active window."""
    try:
        win = gw.getActiveWindow()
        if win:
            return win.title
    except:
        pass
    return None


# ---------------------- Grammar Check ---------------------- #
def process_sentence(sentence):
    """Send sentence to backend and store correction suggestion."""
    global latest_suggestion, latest_original
    #  Removed buffer = "" to keep multi-line state
    if not capture_enabled:
        return

    print("Captured sentence:", sentence)
    try:
        res = requests.post(get_api_key(), json={"text": sentence})
        if res.status_code == 200:
            data = res.json()
            suggestion = data.get("suggestion", "")
            if suggestion and suggestion != sentence:
                latest_original = sentence
                latest_suggestion = suggestion
                print(" Suggestion ready. Hover near text to view correction.")
            else:
                latest_original = None
                latest_suggestion = None
                print(" No correction needed.")
        else:
            print(" Backend error:", res.status_code, res.text)
    except Exception as e:
        print(" Error sending to backend:", e)


# ---------------------- Popup Display ---------------------- #
def show_popup(original, suggestion):
    """Show suggestion popup near mouse cursor."""
    global popup
    hide_popup()

    x, y = pyautogui.position()

    popup = tk.Tk()
    popup.overrideredirect(True)
    popup.attributes('-topmost', True)
    popup.geometry(f"+{x+20}+{y-30}")

    frame = tk.Frame(popup, bg="white", bd=1, relief="solid")
    frame.pack(fill="both", expand=True, padx=6, pady=6)

    tk.Label(frame, text="Suggestion:", font=("Arial", 9, "bold"), bg="white").pack(anchor="w")
    tk.Label(frame, text=suggestion, wraplength=250, bg="white", fg="green").pack(anchor="w", padx=5)

    btn_frame = tk.Frame(frame, bg="white")
    btn_frame.pack(fill="x", pady=(8, 3))

    tk.Button(
        btn_frame, text="Replace", bg="green", fg="white", relief="flat",
        command=lambda: replace_and_close(original, suggestion)
    ).pack(side="left", padx=8)

    tk.Button(
        btn_frame, text="Ignore", bg="gray", fg="white", relief="flat",
        command=hide_popup
    ).pack(side="right", padx=8)

    popup.mainloop()


def hide_popup():
    """Destroy popup if open."""
    global popup
    try:
        if popup and popup.winfo_exists():
            popup.destroy()
    except:
        pass
    popup = None


def replace_and_close(original, suggestion):
    """Replace text and close popup."""
    hide_popup()
    replace_in_text(original, suggestion)
    global latest_suggestion, latest_original, buffer
    latest_suggestion = None
    latest_original = None
    buffer = ""  #  clear any leftover text so idle_check doesn’t re-trigger
    print(" Replaced and closed popup.")



# ---------------------- Replace Logic ---------------------- #
def replace_in_text(original, suggestion):
    """Replace only the last typed sentence cleanly without adding spaces."""
    global capture_enabled
    capture_enabled = False

    try:
        # Copy full current text
        keyboard.press_and_release('ctrl+a')
        time.sleep(0.05)
        keyboard.press_and_release('ctrl+c')
        time.sleep(0.05)
        text = pyperclip.paste()

        original_clean = original.strip()
        suggestion_clean = suggestion.strip()
        idx = text.rfind(original_clean)

        if idx != -1:
            before = text[:idx].rstrip()
            after = text[idx + len(original_clean):].lstrip()
            new_text = before + "\n" + suggestion_clean
            if after:
                if not after.startswith("\n"):
                    new_text += " " + after
                else:
                    new_text += "\n" + after
        else:
            print(" Original not found, replacing last sentence heuristically.")
            last_punc = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            if last_punc != -1:
                new_text = text[:last_punc+1].rstrip() + "\n" + suggestion_clean
            else:
                new_text = suggestion_clean

        keyboard.press_and_release('ctrl+a')
        time.sleep(0.05)
        keyboard.press_and_release('backspace')
        time.sleep(0.05)
        keyboard.write(new_text)
        print(" Cleanly replaced only the last sentence.")

    finally:
        time.sleep(0.5)
        capture_enabled = True


# ---------------------- Keyboard Hook ---------------------- #
def on_key(event):
    """Capture typing globally, ignoring Ctrl shortcuts."""
    global buffer, last_time, last_window
    if not capture_enabled:
        return
    if event.event_type != keyboard.KEY_DOWN:
        return

    #  Detect window change and reset buffer
    current_window = get_active_window_title()
    if last_window != current_window:
        buffer = ""
        last_window = current_window
        print(f" Switched to: {current_window}")
        return

    name = event.name.lower()
    last_time = time.time()

    if name in ['ctrl', 'shift', 'alt', 'caps lock', 'tab', 'esc', 'windows', 'cmd', 'option']:
        return

    if keyboard.is_pressed('ctrl'):
        if name in ['c', 'v', 'x', 'a', 'z', 'y', 's']:
            return

    #  Handle normal typing
    if len(name) == 1:
        buffer += name
        if name in ".?!":
            sentence = buffer.strip()
            if sentence:
                threading.Thread(target=process_sentence, args=(sentence,)).start()
            buffer = ""
    elif name == "space":
        buffer += " "
    elif name == "backspace":
        buffer = buffer[:-1]
    elif name == "enter":
        #  Only trigger grammar check on Ctrl + Enter
        if keyboard.is_pressed("ctrl"):
            sentence = buffer.strip()
            if sentence:
                threading.Thread(target=process_sentence, args=(sentence,)).start()
            buffer = ""
        else:
            buffer += "\n"  # normal newline (no processing)


# ---------------------- Hover Watcher ---------------------- #
def hover_watcher():
    """Show popup when mouse stays still for 1 sec."""
    global latest_original, latest_suggestion
    last_x, last_y = 0, 0
    still_since = None

    while True:
        time.sleep(0.2)
        if latest_suggestion:
            x, y = pyautogui.position()
            if abs(x - last_x) < 2 and abs(y - last_y) < 2:
                if still_since is None:
                    still_since = time.time()
                elif time.time() - still_since >= 1.0:
                    show_popup(latest_original, latest_suggestion)
                    still_since = None
                    while True:
                        time.sleep(0.2)
                        x2, y2 = pyautogui.position()
                        if abs(x2 - x) > 5 or abs(y2 - y) > 5:
                            break
            else:
                still_since = None
            last_x, last_y = x, y


# ---------------------- Idle Check ---------------------- #
def idle_check():
    """Trigger grammar check after 5 seconds of inactivity."""
    global buffer, last_time
    while True:
        time.sleep(1)
        if buffer and (time.time() - last_time > 5):
            sentence = buffer.strip()
            if sentence:
                threading.Thread(target=process_sentence, args=(sentence,)).start()
            buffer = ""


# ---------------------- Start Everything ---------------------- #
keyboard.hook(on_key)
threading.Thread(target=idle_check, daemon=True).start()
threading.Thread(target=hover_watcher, daemon=True).start()

print("⌨ Grammar assistant running — type anywhere (Notepad, browser, WhatsApp Web, etc).")
keyboard.wait()
