import cv2
import mediapipe as mp
import numpy as np
import time
import ctypes
import math
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import os
from collections import deque
import winsound 
import sys

# ==============================================================================
# 1. SİSTEM PERFORMANS AYARLARI
# ==============================================================================
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    pid = os.getpid()
    handle = ctypes.windll.kernel32.OpenProcess(0x100, False, pid)
    ctypes.windll.kernel32.SetPriorityClass(handle, 0x00000080) 
except:
    pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==============================================================================
# 2. AYARLAR
# ==============================================================================
config = {
    "left_click_combo": [4, 8],
    "right_click_combo": [4, 12],
    "click_dist": 30,
    "drag_delay": 0.45
}

FINGER_MAP = {
    "Başparmak + İşaret": [4, 8],
    "Başparmak + Orta": [4, 12],
    "Başparmak + Yüzük": [4, 16],
    "Başparmak + Serçe": [4, 20],
    "İşaret + Orta": [8, 12]
}

# ==============================================================================
# 3. MOUSE MOTORU
# ==============================================================================
class MouseController:
    def __init__(self):
        self.target_x = 0; self.target_y = 0; self.current_x = 0; self.current_y = 0
        self.screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        self.screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        self.running = False; self.is_frozen = False
        self.user32 = ctypes.windll.user32
        self.history = deque(maxlen=5) 
        self.avg_buffer_x = deque(maxlen=2); self.avg_buffer_y = deque(maxlen=2)

    def start(self):
        self.running = True
        threading.Thread(target=self._mouse_loop, daemon=True).start()

    def stop(self): self.running = False

    def update_target(self, x, y):
        if self.is_frozen: return
        padding = 60 
        x = np.interp(x, (padding, 640-padding), (0, self.screen_w))
        y = np.interp(y, (padding, 480-padding), (0, self.screen_h))
        self.history.append((x, y))
        self.avg_buffer_x.append(x); self.avg_buffer_y.append(y)
        self.target_x = sum(self.avg_buffer_x) / len(self.avg_buffer_x)
        self.target_y = sum(self.avg_buffer_y) / len(self.avg_buffer_y)

    def freeze_smart(self):
        self.is_frozen = True
        if len(self.history) >= 3:
            stable_x, stable_y = self.history[0]
            self.current_x = stable_x; self.current_y = stable_y
            self.user32.SetCursorPos(int(self.current_x), int(self.current_y))
        self.avg_buffer_x.clear(); self.avg_buffer_y.clear()

    def unfreeze(self): self.is_frozen = False

    def click(self, button='left', action='click'):
        flags = 0
        if button == 'left':
            if action == 'down': flags = 0x0002
            elif action == 'up': flags = 0x0004
            elif action == 'click': flags = 0x0002 | 0x0004
            elif action == 'double': 
                self.user32.mouse_event(0x0006, 0, 0, 0, 0)
                self.user32.mouse_event(0x0006, 0, 0, 0, 0)
                return
        elif button == 'right': flags = 0x0008 | 0x0010
        if flags: self.user32.mouse_event(flags, 0, 0, 0, 0)

    def _mouse_loop(self):
        while self.running:
            if not self.is_frozen:
                dx = self.target_x - self.current_x; dy = self.target_y - self.current_y
                dist = math.hypot(dx, dy)
                if dist < 1.0: time.sleep(0.001); continue
                
                if dist > 150: smooth = 0.5
                elif dist > 50: smooth = 0.3
                elif dist > 10: smooth = 0.15
                else: smooth = 0.05

                self.current_x += dx * smooth; self.current_y += dy * smooth
                self.current_x = max(0, min(self.screen_w, self.current_x))
                self.current_y = max(0, min(self.screen_h, self.current_y))
                self.user32.SetCursorPos(int(self.current_x), int(self.current_y))
            time.sleep(0.005) 

# ==============================================================================
# 4. GHOSTY BACKEND (HATA YÖNETİMLİ)
# ==============================================================================
def run_ghosty(mode="background", on_finish=None, on_error=None):
    controller = MouseController()
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.5, model_complexity=0)

    # --- 1. GÜVENLİK DUVARI: KAMERA BAŞLATMA ---
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Kamera hiç açılmazsa (RAM Koruması)
    if not cap.isOpened():
        if on_error: on_error("Kamera bulunamadı!\nLütfen bağlantıyı kontrol edip tekrar deneyin.")
        return 
    
    # Kamera başarılıysa motoru başlat
    controller.start()

    left_active = False; drag_active = False; click_start_time = 0
    right_active = False; quit_start_time = 0; is_quitting = False; last_click_release_time = 0
    RELEASE_DIST = config["click_dist"] + 20 
    
    error_occurred = False

    try:
        while True:
            success, frame = cap.read()
            
            # --- 2. GÜVENLİK DUVARI: BAĞLANTI KOPMASI ---
            if not success or frame is None:
                error_occurred = True
                if on_error: on_error("Kamera bağlantısı kesildi!\nUygulama durduruluyor.")
                break 

            frame = cv2.flip(frame, 1)
            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, c = frame.shape
            results = hands.process(frameRGB)

            detected_quit = False
            if results.multi_hand_landmarks and len(results.multi_hand_landmarks) == 2:
                h1, h2 = results.multi_hand_landmarks[0].landmark, results.multi_hand_landmarks[1].landmark
                dist_finger = math.hypot((h1[8].x - h2[8].x)*w, (h1[8].y - h2[8].y)*h)
                dist_wrist = math.hypot((h1[0].x - h2[0].x)*w, (h1[0].y - h2[0].y)*h)
                
                if dist_finger < 40 and dist_wrist > 150:
                    if not is_quitting: is_quitting = True; quit_start_time = time.time()
                    if mode == "test": cv2.putText(frame, "CIKIS...", (50, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,255), 2)
                    if time.time() - quit_start_time > 1.0: winsound.Beep(800, 300); break
                    detected_quit = True
            if not detected_quit: is_quitting = False

            if results.multi_hand_landmarks:
                lm = results.multi_hand_landmarks[0].landmark
                controller.update_target(lm[5].x * w, lm[5].y * h)
                l1, l2 = config["left_click_combo"]; r1, r2 = config["right_click_combo"]
                x1, y1 = lm[l1].x*w, lm[l1].y*h; x2, y2 = lm[l2].x*w, lm[l2].y*h
                dis_left = math.hypot(x2-x1, y2-y1)
                rx1, ry1 = lm[r1].x*w, lm[r1].y*h; rx2, ry2 = lm[r2].x*w, lm[r2].y*h
                dis_right = math.hypot(rx2-rx1, ry2-ry1)

                if dis_left < config["click_dist"]:
                    if not left_active: left_active = True; click_start_time = time.time(); controller.freeze_smart()
                    if left_active and not drag_active:
                        if time.time() - click_start_time > config["drag_delay"]: drag_active = True; controller.unfreeze(); controller.click('left', 'down')
                elif dis_left > RELEASE_DIST:
                    if left_active:
                        if drag_active: controller.click('left', 'up'); drag_active = False
                        else:
                            if (time.time() - last_click_release_time) < 0.4: controller.click('left', 'double'); last_click_release_time = 0
                            else: controller.click('left', 'click'); last_click_release_time = time.time()
                        controller.unfreeze(); left_active = False
                if dis_right < config["click_dist"] and not right_active: controller.freeze_smart(); controller.click('right', 'click'); right_active = True; time.sleep(0.1)
                elif dis_right > RELEASE_DIST:
                    if right_active: controller.unfreeze(); right_active = False
                
                if mode == "test":
                    cv2.circle(frame, (int(lm[8].x*w), int(lm[8].y*h)), 5, (0,255,0), -1)
                    cv2.circle(frame, (int(lm[5].x*w), int(lm[5].y*h)), 5, (255,0,0), -1)
                    cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0,255,255), 2)

            if mode == "test":
                cv2.imshow("Ghosty Test", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
            else: time.sleep(0.005)
    
    except Exception as e:
        if on_error: on_error(f"Beklenmedik bir hata oluştu:\n{e}")
        error_occurred = True

    finally:
        cap.release()
        if mode == "test": cv2.destroyAllWindows()
        controller.stop()
        if on_finish and not error_occurred: on_finish()

# ==============================================================================
# 5. ARAYÜZ (FRONTEND - GÜVENLİ KAPATMA EKLENDİ)
# ==============================================================================

# --- Global Thread Takibi ---
ghosty_thread = None 

def safe_exit():
    """Tüm Tkinter ve Python sürecini garantili sonlandırır."""
    try:
        root.destroy()
    except:
        pass
    os._exit(0) # Güvenli çıkışın garantisi

def on_closing():
    """Penceredeki X tuşuna basıldığında çağrılır."""
    if messagebox.askokcancel("Çıkış", "Ghosty'yi tamamen kapatmak istediğinizden emin misiniz?"):
        safe_exit()

# --- Normal Arayüz Fonksiyonları ---

def save_config():
    global config
    config["left_click_combo"] = FINGER_MAP[left_click_var.get()]
    config["right_click_combo"] = FINGER_MAP[right_click_var.get()]
    config["click_dist"] = int(dist_scale.get())
    config["drag_delay"] = float(delay_scale.get())

def restore_gui():
    root.after(0, lambda: root.deiconify()) 
    root.after(0, lambda: root.state('normal'))

def handle_error(message):
    restore_gui()
    root.after(100, lambda: messagebox.showerror("Ghosty Hata", message))

def thread_bg(): run_ghosty(mode="background", on_finish=restore_gui, on_error=handle_error)
def thread_test(): 
    messagebox.showinfo("Ghosty", "Çıkış için 'q' veya iki parmak hareketi."); 
    root.iconify(); 
    run_ghosty(mode="test", on_finish=restore_gui, on_error=handle_error)

# --- THREAD BAŞLATMA FONKSİYONLARI GÜNCELLENDİ ---

def launch_bg(): 
    global ghosty_thread
    save_config()
    root.iconify()
    ghosty_thread = threading.Thread(target=thread_bg)
    ghosty_thread.start()

def launch_test(): 
    global ghosty_thread
    save_config()
    ghosty_thread = threading.Thread(target=thread_test)
    ghosty_thread.start()

# --- UI TANIMLAMALARI ---
BG_COLOR = "#121212"
CARD_COLOR = "#1E1E1E"
ACCENT_COLOR = "#00ADB5"
TEXT_COLOR = "#EEEEEE"
TEXT_SUB = "#AAAAAA"

root = tk.Tk()
root.title("Ghosty v1.0")
root.configure(bg=BG_COLOR)

try: root.iconbitmap(resource_path("ghosty.ico"))
except: pass

style = ttk.Style()
style.theme_use('clam') 

style.configure("TCombobox", fieldbackground=CARD_COLOR, background=ACCENT_COLOR, foreground=TEXT_COLOR, arrowcolor="white", bordercolor=BG_COLOR, lightcolor=BG_COLOR, darkcolor=BG_COLOR)
style.map('TCombobox', fieldbackground=[('readonly', CARD_COLOR)], selectbackground=[('readonly', CARD_COLOR)], selectforeground=[('readonly', TEXT_COLOR)])

class CyberButton(tk.Button):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.default_bg = kwargs.get('bg', CARD_COLOR)
        self.config(font=("Segoe UI", 11, "bold"), fg="white", activeforeground="white", activebackground=self.lighten(self.default_bg), bd=0, relief="flat", cursor="hand2", padx=20, pady=12)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e): self['bg'] = self.lighten(self.default_bg)
    def on_leave(self, e): self['bg'] = self.default_bg
    def lighten(self, hex_color):
        if hex_color == ACCENT_COLOR: return "#00ced1"
        return "#333333"

# --- ADAPTIVE LAYOUT ---
footer = tk.Frame(root, bg="#1a1a1a", pady=10)
footer.pack(side="bottom", fill="x")
tk.Label(footer, text="PROGRAMI KAPATMAK İÇİN", font=("Segoe UI", 8, "bold"), bg="#1a1a1a", fg="#e74c3c").pack()
tk.Label(footer, text="İki elin işaret parmaklarını birleştir.", font=("Segoe UI", 9), bg="#1a1a1a", fg="#7f8c8d").pack()

header = tk.Frame(root, bg=BG_COLOR, pady=15)
header.pack(fill="x")
tk.Label(header, text="GHOSTY", font=("Segoe UI", 24, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack()
tk.Label(header, text="TEMASSIZ KONTROL", font=("Segoe UI", 9, "bold"), bg=BG_COLOR, fg=TEXT_SUB, pady=2).pack()

card = tk.Frame(root, bg=CARD_COLOR, padx=20, pady=15)
card.pack(fill="x", padx=20, pady=5)

def create_label(parent, text):
    tk.Label(parent, text=text, font=("Segoe UI", 9), bg=CARD_COLOR, fg=TEXT_SUB, anchor="w").pack(fill="x", pady=(10, 2))

create_label(card, "SOL TIK HAREKETİ")
left_click_var = tk.StringVar(value="Başparmak + İşaret")
cb_left = ttk.Combobox(card, textvariable=left_click_var, values=list(FINGER_MAP.keys()), state="readonly", font=("Segoe UI", 10))
cb_left.pack(fill="x", ipady=2)

create_label(card, "SAĞ TIK HAREKETİ")
right_click_var = tk.StringVar(value="Başparmak + Serçe")
cb_right = ttk.Combobox(card, textvariable=right_click_var, values=list(FINGER_MAP.keys()), state="readonly", font=("Segoe UI", 10))
cb_right.pack(fill="x", ipady=2)

create_label(card, "HASSASİYET")
dist_scale = tk.Scale(card, from_=15, to=60, orient=tk.HORIZONTAL, bg=CARD_COLOR, fg=ACCENT_COLOR, troughcolor="#333", highlightthickness=0, activebackground=ACCENT_COLOR)
dist_scale.set(30)
dist_scale.pack(fill="x")

create_label(card, "SÜRÜKLEME GECİKMESİ")
delay_scale = tk.Scale(card, from_=0.2, to=1.0, resolution=0.1, orient=tk.HORIZONTAL, bg=CARD_COLOR, fg=ACCENT_COLOR, troughcolor="#333", highlightthickness=0, activebackground=ACCENT_COLOR)
delay_scale.set(1) 
delay_scale.pack(fill="x")

btn_frame = tk.Frame(root, bg=BG_COLOR, pady=15)
btn_frame.pack(fill="x", padx=20)

btn_test = CyberButton(btn_frame, text="TEST MODU", bg="#34495e", command=launch_test)
btn_test.pack(fill="x", pady=(0, 8))

btn_start = CyberButton(btn_frame, text="BAŞLAT", bg=ACCENT_COLOR, command=launch_bg)
btn_start.pack(fill="x")

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    max_height = screen_height - 80 
    if height > max_height: height = max_height
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    if y < 0: y = 0
    window.geometry(f'{width}x{height}+{x}+{y}')

center_window(root, 450, 780)
root.protocol("WM_DELETE_WINDOW", on_closing) 
root.mainloop()