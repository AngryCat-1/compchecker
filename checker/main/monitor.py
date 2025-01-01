import time
from pynput import mouse, keyboard
from threading import Thread
from collections import defaultdict
import platform

if platform.system() == "Windows":
    import win32gui
elif platform.system() == "Linux":
    from Xlib import display


last_activity_time = time.time()
start_time = time.time()
app_usage = defaultdict(lambda: {'time_seconds': 0})
current_app = None

def update_last_activity():
    global last_activity_time
    last_activity_time = time.time()

def mouse_listener():
    with mouse.Listener(on_move=lambda x, y: update_last_activity()) as listener:
        listener.join()

def keyboard_listener():
    with keyboard.Listener(on_press=lambda key: update_last_activity()) as listener:
        listener.join()

def get_active_application():
    if platform.system() == "Windows":
        window = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(window)
    elif platform.system() == "Linux":
        d = display.Display()
        root = d.screen().root
        window_id = root.get_full_property(d.intern_atom('_NET_ACTIVE_WINDOW'), 0).value[0]
        window = d.create_resource_object('window', window_id)
        return window.get_wm_name()
    return "Unknown"

def track_active_application():
    global current_app
    start_time = time.time()

    while True:
        active_app = get_active_application()
        if active_app != current_app:
            if current_app:
                elapsed_time = time.time() - start_time
                elapsed_minutes = round(elapsed_time, 1)
                app_usage[current_app]['time_seconds'] += elapsed_minutes
            current_app = active_app
            start_time = time.time()

        time.sleep(1)

def start_activity_monitor():
    Thread(target=mouse_listener, daemon=True).start()
    Thread(target=keyboard_listener, daemon=True).start()
    Thread(target=track_active_application, daemon=True).start()

def get_app_usage():
    return dict(app_usage)

start_activity_monitor()
