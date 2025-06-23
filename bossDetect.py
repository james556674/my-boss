import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import pyautogui
import cv2
import numpy as np

# A simple state machine for our bot
class BotState:
    LOGIN_SCREEN = "LOGIN_SCREEN"
    CHAR_SELECT = "CHAR_SELECT"
    IN_GAME_SCANNING = "IN_GAME_SCANNING"
    OPENING_CHANNEL_LIST = "OPENING_CHANNEL_LIST"
    SWITCHING_CHANNEL = "SWITCHING_CHANNEL"
    STOPPED = "STOPPED"


class GameBot:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Artale Boss Hunter")
        self.root.geometry("550x700")

        self.bot_thread = None
        self.is_running = False
        self.current_state = BotState.STOPPED

        self.templates = {
            "login_button": None,
            "char_select_button": None,
            "boss_indicator": None,
            "menu_channel_button": None,
            "switch_channel_button": None,
            "confirm_button": None,
        }
        self.setup_gui()

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Template Loading ---
        template_frame = ttk.LabelFrame(main_frame, text="1. 載入所有模板圖片", padding="10")
        template_frame.pack(fill=tk.X, expand=True, pady=5)
        
        self.template_labels = {}
        for key, name in {
            "login_button": "登入遊戲 按鈕",
            "char_select_button": "選擇角色 按鈕",
            "boss_indicator": "Boss 出現指示器",
            "menu_channel_button": "ESC選單中的[頻道]按鈕",
            "switch_channel_button": "頻道列表中的[換頻]按鈕",
            "confirm_button": "確認換頻 按鈕"
        }.items():
            ttk.Button(template_frame, text=f"載入 {name}", command=lambda k=key: self.load_template(k)).pack(fill=tk.X, pady=2)
            label = ttk.Label(template_frame, text="狀態: 未載入")
            label.pack()
            self.template_labels[key] = label

        # --- Controls ---
        control_frame = ttk.LabelFrame(main_frame, text="2. 控制", padding="10")
        control_frame.pack(fill=tk.X, expand=True, pady=5)
        self.start_button = ttk.Button(control_frame, text="開始掛機", command=self.start_bot)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.stop_button = ttk.Button(control_frame, text="停止", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # --- Status & Log ---
        status_frame = ttk.LabelFrame(main_frame, text="3. 狀態與日誌", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.status_label = ttk.Label(status_frame, text="當前狀態: 已停止", font=("Arial", 12))
        self.status_label.pack(pady=5)
        self.log_text = tk.Text(status_frame, height=12, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def update_status(self, text):
        self.status_label.config(text=f"當前狀態: {text}")
        self.log(f"狀態變更 -> {text}")

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def load_template(self, key):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if not path: return
        image = cv2.imread(path)
        if image is None:
            messagebox.showerror("錯誤", "無法讀取圖片")
            return
        self.templates[key] = image
        self.template_labels[key].config(text=f"狀態: 已載入 ({path.split('/')[-1]})")
        self.log(f"成功載入模板: {key}")

    def find_and_click(self, template_key, confidence=0.8, timeout=5):
        self.log(f"正在尋找 [{template_key}]...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running: return None
            
            screenshot = pyautogui.screenshot()
            screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            template = self.templates[template_key]

            if template.shape[0] > screen_cv.shape[0] or template.shape[1] > screen_cv.shape[1]:
                self.log(f"錯誤: [{template_key}] 模板比螢幕大")
                return None
            
            result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= confidence:
                h, w, _ = template.shape
                center_pos = (max_loc[0] + w // 2, max_loc[1] + h // 2)
                self.log(f"  > 找到 [{template_key}] 於 {center_pos}，點擊它。")
                pyautogui.click(center_pos)
                return center_pos
            
            time.sleep(0.5)
        
        self.log(f"錯誤: {timeout}秒內找不到 [{template_key}]")
        return None
    
    def scan_for_boss(self, duration=10):
        self.log(f"開始掃描 Boss，持續 {duration} 秒...")
        start_time = time.time()
        while time.time() - start_time < duration:
            if not self.is_running: return False
            if self.find_and_click("boss_indicator", timeout=0.5): # Quick check
                self.log("🎉🎉🎉 偵測到 BOSS！ 🎉🎉🎉")
                return True
            time.sleep(1) # Wait 1 sec before next scan
        self.log("掃描結束，未發現 Boss。")
        return False

    def start_bot(self):
        if any(t is None for t in self.templates.values()):
            messagebox.showwarning("模板未載入", "請先載入所有模板圖片！")
            return
        
        self.is_running = True
        self.current_state = BotState.LOGIN_SCREEN
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        self.bot_thread = threading.Thread(target=self.main_loop, daemon=True)
        self.bot_thread.start()

    def stop_bot(self):
        if not self.is_running: return
        self.is_running = False
        self.current_state = BotState.STOPPED
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.update_status("已手動停止")

    def main_loop(self):
        while self.is_running:
            self.update_status(self.current_state)
            
            if self.current_state == BotState.LOGIN_SCREEN:
                if self.find_and_click("login_button"):
                    self.current_state = BotState.CHAR_SELECT
                    time.sleep(5) # Wait for char screen to load
                else:
                    self.stop_bot()

            elif self.current_state == BotState.CHAR_SELECT:
                if self.find_and_click("char_select_button"):
                    self.current_state = BotState.IN_GAME_SCANNING
                    time.sleep(10) # Wait for game to load
                else:
                    self.stop_bot()

            elif self.current_state == BotState.IN_GAME_SCANNING:
                if self.scan_for_boss():
                    self.stop_bot() # Found boss, stop the bot
                else:
                    # No boss found, proceed to change channel
                    self.current_state = BotState.OPENING_CHANNEL_LIST
            
            elif self.current_state == BotState.OPENING_CHANNEL_LIST:
                pyautogui.press('esc')
                self.log("按下 ESC 鍵")
                time.sleep(1)
                if self.find_and_click("menu_channel_button"):
                    self.current_state = BotState.SWITCHING_CHANNEL
                    time.sleep(2) # Wait for channel list to appear
                else:
                    self.stop_bot() # Failed to open channel list
            
            elif self.current_state == BotState.SWITCHING_CHANNEL:
                if not self.find_and_click("switch_channel_button"):
                    self.stop_bot()
                    continue
                time.sleep(1)
                if not self.find_and_click("confirm_button"):
                    self.stop_bot()
                    continue
                
                # After confirming, wait for game to load and go back to scanning
                self.log("頻道切換中，等待15秒...")
                time.sleep(15)
                self.current_state = BotState.IN_GAME_SCANNING
                
        self.log("主循環已結束。")

    def run_gui(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.2
        self.root.mainloop()

if __name__ == "__main__":
    bot = GameBot()
    bot.run_gui()
