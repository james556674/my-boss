import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import pyautogui
import cv2
import numpy as np

# Using the previous scene-aware state machine
class BotState:
    DETERMINING_STATE = "DETERMINING_STATE"
    LOGIN_SCREEN = "LOGIN_SCREEN"
    CHAR_SELECT = "CHAR_SELECT"
    IN_GAME_SCANNING = "IN_GAME_SCANNING"
    OPENING_CHANNEL_LIST = "OPENING_CHANNEL_LIST"
    SWITCHING_CHANNEL = "SWITCHING_CHANNEL"
    STOPPED = "STOPPED"


class GameBot:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Artale Boss Hunter (Optimized)")
        self.root.geometry("550x850") # Adjusted height for confidence slider

        self.bot_thread = None
        self.is_running = False
        self.current_state = BotState.STOPPED

        self.templates = {
            "login_scene_indicator": None, "char_select_scene_indicator": None,
            "login_button": None, "char_select_button": None, "boss_indicator": None,
            "menu_channel_button": None, "switch_channel_button": None, "confirm_button": None,
        }
        self.setup_gui()

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Template Loading (remains the same) ---
        template_frame = ttk.LabelFrame(main_frame, text="1. 載入所有模板圖片", padding="10")
        template_frame.pack(fill=tk.X, expand=True, pady=5)
        self.template_labels = {}
        ttk.Label(template_frame, text="--- 場景指示器 ---", font=("Arial", 10, "bold")).pack(pady=(5,0))
        for key, name in {"login_scene_indicator": "登入畫面 指示器", "char_select_scene_indicator": "選角畫面 指示器"}.items():
            ttk.Button(template_frame, text=f"載入 {name}", command=lambda k=key: self.load_template(k)).pack(fill=tk.X, pady=2)
            label = ttk.Label(template_frame, text="狀態: 未載入"); label.pack(); self.template_labels[key] = label
        ttk.Label(template_frame, text="--- 動作按鈕 ---", font=("Arial", 10, "bold")).pack(pady=(10,0))
        for key, name in {"login_button": "登入遊戲 按鈕", "char_select_button": "選擇角色 按鈕", "boss_indicator": "Boss 出現指示器", "menu_channel_button": "ESC選單中的[頻道]按鈕", "switch_channel_button": "頻道列表中的[換頻]按鈕", "confirm_button": "確認換頻 按鈕"}.items():
            ttk.Button(template_frame, text=f"載入 {name}", command=lambda k=key: self.load_template(k)).pack(fill=tk.X, pady=2)
            label = ttk.Label(template_frame, text="狀態: 未載入"); label.pack(); self.template_labels[key] = label

        # --- Settings Frame with Confidence Slider ---
        settings_frame = ttk.LabelFrame(main_frame, text="2. 辨識設定", padding="10")
        settings_frame.pack(fill=tk.X, expand=True, pady=5)
        ttk.Label(settings_frame, text="辨識信心度 (越高越嚴格):").pack(anchor='w')
        self.confidence_var = tk.DoubleVar(value=0.8)
        self.confidence_scale = ttk.Scale(settings_frame, from_=0.5, to=0.95, orient=tk.HORIZONTAL, variable=self.confidence_var)
        self.confidence_scale.pack(fill=tk.X, pady=5)
        self.confidence_label = ttk.Label(settings_frame, text=f"{self.confidence_var.get():.2f}")
        self.confidence_label.pack()
        self.confidence_scale.config(command=lambda v: self.confidence_label.config(text=f"{float(v):.2f}"))


        # --- Controls ---
        control_frame = ttk.LabelFrame(main_frame, text="3. 控制", padding="10")
        control_frame.pack(fill=tk.X, expand=True, pady=5)
        self.start_button = ttk.Button(control_frame, text="開始掛機", command=self.start_bot)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.stop_button = ttk.Button(control_frame, text="停止", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # Add test button for debugging
        test_frame = ttk.Frame(control_frame)
        test_frame.pack(fill=tk.X, pady=5)
        ttk.Button(test_frame, text="測試登入按鈕識別", command=self.test_login_button).pack(fill=tk.X)
        ttk.Button(test_frame, text="測試Boss指示器識別", command=self.test_boss_indicator).pack(fill=tk.X)
        ttk.Button(test_frame, text="模擬實際掃描流程", command=self.simulate_scanning).pack(fill=tk.X)
        ttk.Button(test_frame, text="詳細Boss偵測分析", command=self.detailed_boss_analysis).pack(fill=tk.X)

        # --- Status & Log ---
        status_frame = ttk.LabelFrame(main_frame, text="4. 狀態與日誌", padding="10")
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
        # Load as grayscale directly for consistency
        image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            messagebox.showerror("錯誤", "無法讀取圖片")
            return
        self.templates[key] = image
        self.template_labels[key].config(text=f"狀態: 已載入 ({path.split('/')[-1]})")
        self.log(f"成功載入灰階模板: {key}")

    def is_image_on_screen(self, template_key):
        if self.templates[template_key] is None: return False
        
        # Take screenshot and convert to grayscale
        screenshot = pyautogui.screenshot()
        screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        
        template = self.templates[template_key]
        if template.shape[0] > screen_cv.shape[0] or template.shape[1] > screen_cv.shape[1]:
            return False

        # Match using the grayscale template on the grayscale screen
        result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        # Use confidence from the slider
        return max_val >= self.confidence_var.get()

    def find_and_click(self, template_key, timeout=5):
        self.log(f"正在尋找並點擊 [{template_key}]...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running: return None
            
            # Convert screen to grayscale for matching
            screenshot = pyautogui.screenshot()
            screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            template = self.templates[template_key]

            if template.shape[0] > screen_cv.shape[0] or template.shape[1] > screen_cv.shape[1]:
                self.log(f"錯誤: [{template_key}] 模板比螢幕大")
                return None
            
            result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= self.confidence_var.get():
                h, w = template.shape # Get shape from grayscale template
                
                center_pos = (max_loc[0] + w // 2, max_loc[1] + h // 2)
                self.log(f"  > 找到 [{template_key}] 於 {center_pos}，信心度 {max_val:.2f}，點擊它。")
                pyautogui.click(center_pos)
                # 立即返回，不等待
                return center_pos
            else:
                # Add debugging info for login button specifically
                if template_key == "login_button":
                    self.log(f"  > 當前最高信心度: {max_val:.3f} (需要 {self.confidence_var.get():.3f})")
                # Add debugging info for character select button
                elif template_key == "char_select_button":
                    self.log(f"  > 當前最高信心度: {max_val:.3f} (需要 {self.confidence_var.get():.3f})")
            
            time.sleep(0.1)
        
        self.log(f"提示: {timeout}秒內找不到 [{template_key}]")
        return None

    def scan_for_boss(self, duration=15):
        self.log(f"開始掃描 Boss，持續 {duration} 秒...")
        start_time = time.time()
        scan_count = 0
        while time.time() - start_time < duration:
            if not self.is_running: return False
            
            scan_count += 1
            # 檢查 Boss 指示器
            if self.is_image_on_screen("boss_indicator"):
                self.log("🎉🎉🎉 偵測到 BOSS！ 🎉🎉🎉")
                return True
            else:
                # 每10次掃描顯示一次調試資訊（因為現在掃描更頻繁）
                if scan_count % 10 == 0:
                    # 獲取當前信心度
                    screenshot = pyautogui.screenshot()
                    screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
                    template = self.templates["boss_indicator"]
                    result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    self.log(f"掃描中... 第{scan_count}次檢查，Boss指示器最高信心度: {max_val:.3f} (需要 {self.confidence_var.get():.3f})")
                    
                    # 如果信心度接近但未達到閾值，記錄下來
                    if max_val >= self.confidence_var.get() * 0.7:  # 70% 的閾值
                        self.log(f"⚠️ 接近偵測閾值！信心度: {max_val:.3f}")
                        # 保存接近閾值的截圖
                        screenshot.save(f"near_threshold_{int(time.time())}.png")
                        self.log("已保存接近閾值的截圖")
            
            time.sleep(0.1)  # 更頻繁的檢查
        
        self.log("掃描結束，未發現 Boss。")
        return False

    def start_bot(self):
        if any(t is None for t in self.templates.values()):
            messagebox.showwarning("模板未載入", "請先載入所有模板圖片！")
            return
        
        self.is_running = True
        self.current_state = BotState.DETERMINING_STATE
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

    def test_login_button(self):
        """測試登入按鈕識別功能"""
        if self.templates["login_button"] is None:
            messagebox.showwarning("錯誤", "請先載入登入按鈕模板！")
            return
        
        self.log("=== 開始測試登入按鈕識別 ===")
        
        # 截圖並轉換為灰階
        screenshot = pyautogui.screenshot()
        screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        template = self.templates["login_button"]
        
        # 檢查模板大小
        self.log(f"螢幕大小: {screen_cv.shape[1]}x{screen_cv.shape[0]}")
        self.log(f"模板大小: {template.shape[1]}x{template.shape[0]}")
        
        if template.shape[0] > screen_cv.shape[0] or template.shape[1] > screen_cv.shape[1]:
            self.log("錯誤: 模板比螢幕大！")
            return
        
        # 進行模板匹配
        result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        self.log(f"最高信心度: {max_val:.4f}")
        self.log(f"最佳匹配位置: {max_loc}")
        self.log(f"當前信心度設定: {self.confidence_var.get():.2f}")
        
        if max_val >= self.confidence_var.get():
            h, w = template.shape
            center_pos = (max_loc[0] + w // 2, max_loc[1] + h // 2)
            self.log(f"✅ 找到登入按鈕！位置: {center_pos}")
            
            # 詢問是否要點擊
            if messagebox.askyesno("測試", f"找到登入按鈕於位置 {center_pos}\n信心度: {max_val:.4f}\n是否要點擊？"):
                pyautogui.click(center_pos)
                self.log("已點擊登入按鈕")
        else:
            self.log("❌ 未找到登入按鈕")
            self.log("建議:")
            self.log("1. 降低信心度設定")
            self.log("2. 重新截取登入按鈕模板")
            self.log("3. 確認遊戲視窗在最前面")
        
        self.log("=== 測試結束 ===")

    def test_boss_indicator(self):
        """測試Boss指示器識別功能"""
        if self.templates["boss_indicator"] is None:
            messagebox.showwarning("錯誤", "請先載入Boss指示器模板！")
            return
        
        self.log("=== 開始測試Boss指示器識別 ===")
        
        # 截圖並轉換為灰階
        screenshot = pyautogui.screenshot()
        screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        template = self.templates["boss_indicator"]
        
        # 檢查模板大小
        self.log(f"螢幕大小: {screen_cv.shape[1]}x{screen_cv.shape[0]}")
        self.log(f"模板大小: {template.shape[1]}x{template.shape[0]}")
        
        if template.shape[0] > screen_cv.shape[0] or template.shape[1] > screen_cv.shape[1]:
            self.log("錯誤: 模板比螢幕大！")
            return
        
        # 進行模板匹配
        result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        self.log(f"最高信心度: {max_val:.4f}")
        self.log(f"最佳匹配位置: {max_loc}")
        self.log(f"當前信心度設定: {self.confidence_var.get():.2f}")
        
        if max_val >= self.confidence_var.get():
            h, w = template.shape
            center_pos = (max_loc[0] + w // 2, max_loc[1] + h // 2)
            self.log(f"✅ 找到Boss指示器！位置: {center_pos}")
            
            # 詢問是否要點擊
            if messagebox.askyesno("測試", f"找到Boss指示器於位置 {center_pos}\n信心度: {max_val:.4f}\n是否要點擊？"):
                pyautogui.click(center_pos)
                self.log("已點擊Boss指示器")
        else:
            self.log("❌ 未找到Boss指示器")
            self.log("建議:")
            self.log("1. 降低信心度設定")
            self.log("2. 重新截取Boss指示器模板")
            self.log("3. 確認遊戲視窗在最前面")
        
        self.log("=== 測試結束 ===")

    def simulate_scanning(self):
        """模擬實際掃描流程"""
        if self.templates["boss_indicator"] is None:
            messagebox.showwarning("錯誤", "請先載入Boss指示器模板！")
            return
        
        self.log("=== 開始模擬實際掃描流程 ===")
        self.log("這將模擬機器人實際運行時的掃描過程...")
        
        # 詢問用戶是否準備好
        if not messagebox.askyesno("模擬掃描", "請確保遊戲視窗在最前面，然後點擊確定開始模擬掃描"):
            return
        
        # 模擬實際的掃描過程
        duration = 10  # 模擬10秒掃描
        self.log(f"開始模擬掃描，持續 {duration} 秒...")
        
        start_time = time.time()
        scan_count = 0
        while time.time() - start_time < duration:
            scan_count += 1
            
            # 檢查 Boss 指示器
            if self.is_image_on_screen("boss_indicator"):
                self.log("🎉🎉🎉 模擬掃描中偵測到 BOSS！ 🎉🎉🎉")
                return
            
            # 每2秒顯示一次調試資訊
            if scan_count % 20 == 0:  # 因為現在是0.1秒間隔，所以20次=2秒
                screenshot = pyautogui.screenshot()
                screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
                template = self.templates["boss_indicator"]
                result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                self.log(f"模擬掃描中... 信心度: {max_val:.3f} (需要 {self.confidence_var.get():.3f})")
            
            time.sleep(0.1)
        
        self.log("模擬掃描結束，未發現 Boss。")
        self.log("=== 模擬掃描結束 ===")

    def detailed_boss_analysis(self):
        """詳細Boss偵測分析"""
        if self.templates["boss_indicator"] is None:
            messagebox.showwarning("錯誤", "請先載入Boss指示器模板！")
            return
        
        self.log("=== 開始詳細Boss偵測分析 ===")
        
        # 保存當前截圖
        screenshot = pyautogui.screenshot()
        screenshot.save(f"current_screen_{int(time.time())}.png")
        self.log("已保存當前螢幕截圖")
        
        # 轉換為灰階
        screen_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
        template = self.templates["boss_indicator"]
        
        # 進行模板匹配
        result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        self.log(f"=== 詳細分析結果 ===")
        self.log(f"螢幕大小: {screen_cv.shape[1]}x{screen_cv.shape[0]}")
        self.log(f"模板大小: {template.shape[1]}x{template.shape[0]}")
        self.log(f"最高信心度: {max_val:.4f}")
        self.log(f"最佳匹配位置: {max_loc}")
        self.log(f"當前信心度設定: {self.confidence_var.get():.2f}")
        self.log(f"是否達到閾值: {'是' if max_val >= self.confidence_var.get() else '否'}")
        
        # 顯示前5個最佳匹配位置
        self.log("前5個最佳匹配位置:")
        for i in range(min(5, len(result.flatten()))):
            # 找到第i個最大值的位置
            flat_result = result.flatten()
            indices = np.argsort(flat_result)[::-1]
            row, col = np.unravel_index(indices[i], result.shape)
            confidence = flat_result[indices[i]]
            self.log(f"  位置 {i+1}: ({col}, {row}), 信心度: {confidence:.4f}")
        
        # 分析模板的統計資訊
        template_mean = np.mean(template)
        template_std = np.std(template)
        screen_mean = np.mean(screen_cv)
        screen_std = np.std(screen_cv)
        
        self.log(f"=== 統計分析 ===")
        self.log(f"模板平均值: {template_mean:.2f}")
        self.log(f"模板標準差: {template_std:.2f}")
        self.log(f"螢幕平均值: {screen_mean:.2f}")
        self.log(f"螢幕標準差: {screen_std:.2f}")
        
        self.log("=== 詳細分析結束 ===")

    def determine_initial_state(self):
        self.log("正在判斷當前遊戲場景...")
        
        # 嘗試多次識別場景，給遊戲更多載入時間
        for attempt in range(5):  # 嘗試5次
            self.log(f"第 {attempt + 1} 次嘗試識別場景...")
            
            # 先檢查是否在登入畫面
            if self.is_image_on_screen("login_scene_indicator"):
                self.log("判斷結果: 位於登入畫面。")
                return BotState.LOGIN_SCREEN
            # 再檢查是否在角色選擇畫面
            elif self.is_image_on_screen("char_select_scene_indicator"):
                self.log("判斷結果: 位於角色選擇畫面。")
                return BotState.CHAR_SELECT
            
            # 如果不是最後一次嘗試，等待一下再重試
            if attempt < 4:
                self.log("無法識別場景，等待2秒後重試...")
                time.sleep(2)
        
        # 如果5次都無法識別，回到登入畫面重新開始
        self.log("5次嘗試後仍無法識別場景，回到登入畫面重新開始...")
        return BotState.LOGIN_SCREEN

    def main_loop(self):
        while self.is_running:
            self.update_status(self.current_state)
            
            if self.current_state == BotState.DETERMINING_STATE:
                self.current_state = self.determine_initial_state()
                if self.current_state == BotState.STOPPED: self.stop_bot()
            elif self.current_state == BotState.LOGIN_SCREEN:
                if not self.is_image_on_screen("login_scene_indicator"):
                    self.log("錯誤: 登入畫面的指示器消失了，重新判斷場景。")
                    self.current_state = BotState.DETERMINING_STATE
                    continue
                self.log("場景已確認，等待2秒確保按鈕載入...")
                time.sleep(2)
                if self.find_and_click("login_button"):
                    self.log("點擊登入按鈕成功，等待畫面切換...")
                    time.sleep(5)
                    self.current_state = BotState.DETERMINING_STATE
                else: self.stop_bot()
            elif self.current_state == BotState.CHAR_SELECT:
                self.log("進入角色選擇狀態，等待1秒確保畫面載入...")
                time.sleep(1)
                
                # 先確認我們還在角色選擇畫面
                if not self.is_image_on_screen("char_select_scene_indicator"):
                    self.log("錯誤: 角色選擇畫面的指示器消失了，重新判斷場景。")
                    self.current_state = BotState.DETERMINING_STATE
                    continue
                
                if self.find_and_click("char_select_button", timeout=3):
                    self.log("點擊角色選擇成功，立即開始掃描 Boss...")
                    self.current_state = BotState.IN_GAME_SCANNING
                else:
                    self.log("找不到角色選擇按鈕，重新判斷場景...")
                    self.current_state = BotState.DETERMINING_STATE
            elif self.current_state == BotState.IN_GAME_SCANNING:
                if self.scan_for_boss(): self.stop_bot()
                else: self.current_state = BotState.OPENING_CHANNEL_LIST
            elif self.current_state == BotState.OPENING_CHANNEL_LIST:
                pyautogui.press('esc')
                time.sleep(1)
                if self.find_and_click("menu_channel_button"):
                    self.current_state = BotState.SWITCHING_CHANNEL
                    time.sleep(2)
                else:
                    self.log("在ESC選單中找不到頻道按鈕，回到遊戲中...")
                    pyautogui.press('esc')
                    self.current_state = BotState.IN_GAME_SCANNING
            elif self.current_state == BotState.SWITCHING_CHANNEL:
                if not self.find_and_click("switch_channel_button"): self.stop_bot(); continue
                time.sleep(1)
                if not self.find_and_click("confirm_button"): self.stop_bot(); continue
                self.log("頻道切換中，等待15秒讓遊戲重新載入...")
                time.sleep(15)
                self.log("頻道切換完成，重新判斷遊戲場景...")
                self.current_state = BotState.DETERMINING_STATE
        self.log("主循環已結束。")

    def run_gui(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.2
        self.root.mainloop()

if __name__ == "__main__":
    bot = GameBot()
    bot.run_gui()
