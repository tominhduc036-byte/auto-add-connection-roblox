"""
auto_friend.py
Mẫu: GUI Tkinter + Selenium để tự động gửi lời mời và xóa bạn.
Đã chỉnh: dùng JavaScript click cho nút login + nút Add Connection.
Đã thêm: bỏ qua userId 404 (request-error?code=404).
Đã xóa: messagebox báo lỗi khi login thất bại.
Đã cập nhật: logic auto_unfriend mới (truy cập profile để xóa).
"""

import random, time, threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ---------------------------
# Core automation class
# ---------------------------
class AutoFriendBot:
    def __init__(self, status_callback):
        self.driver = None
        self.wait = None
        self.status = status_callback
        self.logged_in_username = None
        self.stop_flag = False

    def stop(self):
        """Stop any running loops"""
        self.stop_flag = True
        self.status("Stop signal received.")

    def reset_stop(self):
        self.stop_flag = False

    def start_browser(self, headless=False):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        self.wait = WebDriverWait(self.driver, 15)
        self.status("Browser started.")

    def login(self, login_url, username, password,
              username_selector, password_selector, submit_selector,
              username_display_selector=None):
        if not self.driver:
            self.start_browser()

        self.status(f"Opening {login_url}")
        self.driver.get(login_url)
        try:
            self.status("Filling credentials...")
            el_user = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, username_selector)))
            el_user.clear()
            el_user.send_keys(username)

            el_pass = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, password_selector)))
            el_pass.clear()
            el_pass.send_keys(password)

            # JS click thay vì .click()
            btn = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, submit_selector)))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", btn)

            self.status("Submitted login form. Waiting for page load...")

            if username_display_selector:
                el_name = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, username_display_selector)))
                self.logged_in_username = el_name.text.strip()
                self.status(f"Đăng nhập thành công — User: {self.logged_in_username}")
                return True
            else:
                time.sleep(3)
                self.status("Login submitted (no display selector provided). Verify manually.")
                return True
        except Exception as e:
            self.status(f"Login failed: {e}")
            return False

    def send_friend_request_by_id(self, add_button_selector,
                                  how_many=10, delay_between=2,
                                  id_min=173, id_max=10_000_000_000,
                                  infinite=False):
        if not self.driver:
            self.status("Browser not started.")
            return

        sent = 0
        self.reset_stop()

        i = 0
        while infinite or i < how_many:
            if self.stop_flag:
                self.status("Stopped by user during friend requests.")
                break

            user_id = random.randint(id_min, id_max)
            profile_url = f"https://www.roblox.com/users/{user_id}/profile"
            try:
                self.driver.get(profile_url)
                self.status(f"Opening {profile_url} ({i+1}/{how_many if not infinite else '∞'})")

                # 🚨 Kiểm tra nếu user không tồn tại (404)
                if "request-error?code=404" in self.driver.current_url:
                    self.status(f"UserId={user_id} không tồn tại → try another user...")
                    continue  # bỏ qua vòng này, không tăng i

                # JS click thay vì .click()
                add_btn = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, add_button_selector)))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", add_btn)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", add_btn)

                self.status(f"Sent friend request to userId={user_id}")
                sent += 1
                i += 1  # chỉ tăng khi gửi thành công
            except Exception as e:
                self.status(f"Failed for userId={user_id}: {e}")
                i += 1  # tăng để không bị lặp vô hạn nếu gặp lỗi khác

            time.sleep(delay_between)

        self.status(f"Done sending. Success: {sent}")

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self.status("Browser closed.")


# ---------------------------
# GUI
# ---------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("Auto Friend Tool - Roblox")
        self.bot = AutoFriendBot(self.add_status)

        # Frame: Login
        frm = tk.Frame(root)
        frm.pack(padx=8, pady=6, fill="x")

        tk.Label(frm, text="Login URL").grid(row=0, column=0, sticky="w")
        self.login_url = tk.Entry(frm, width=60)
        self.login_url.grid(row=0, column=1, columnspan=3, sticky="w")
        self.login_url.insert(0, "https://www.roblox.com/login")

        tk.Label(frm, text="Username").grid(row=1, column=0, sticky="w")
        self.entry_user = tk.Entry(frm)
        self.entry_user.grid(row=1, column=1)
        tk.Label(frm, text="Password").grid(row=1, column=2, sticky="w")
        self.entry_pass = tk.Entry(frm, show="*")
        self.entry_pass.grid(row=1, column=3)

        tk.Label(frm, text="Username display selector").grid(row=2, column=0, sticky="w")
        self.sel_display = tk.Entry(frm, width=40)
        self.sel_display.grid(row=2, column=1, columnspan=3, sticky="w")
        self.sel_display.insert(0, ".profile-name")

        tk.Button(frm, text="Login", command=self.thread_login).grid(row=3, column=0, pady=6)
        tk.Button(frm, text="Close Browser", command=self.bot.close).grid(row=3, column=1, pady=6)

        # Frame: Send invites by userId
        frm2 = tk.LabelFrame(root, text="Gửi lời mời bằng userId")
        frm2.pack(padx=8, pady=6, fill="x")

        tk.Label(frm2, text="Add button selector").grid(row=0, column=0, sticky="w")
        self.sel_add = tk.Entry(frm2, width=40)
        self.sel_add.grid(row=0, column=1, sticky="w")
        self.sel_add.insert(0, "button#friend-button")

        tk.Label(frm2, text="How many").grid(row=1, column=0, sticky="w")
        self.how_many = tk.Entry(frm2, width=8)
        self.how_many.grid(row=1, column=1, sticky="w")
        self.how_many.insert(0, "10")

        tk.Label(frm2, text="ID min").grid(row=2, column=0, sticky="w")
        self.id_min = tk.Entry(frm2, width=12)
        self.id_min.grid(row=2, column=1, sticky="w")
        self.id_min.insert(0, "173")

        tk.Label(frm2, text="ID max").grid(row=2, column=2, sticky="w")
        self.id_max = tk.Entry(frm2, width=12)
        self.id_max.grid(row=2, column=3, sticky="w")
        self.id_max.insert(0, "10000000000")

        # Infinite mode checkbox
        self.var_infinite = tk.BooleanVar()
        tk.Checkbutton(frm2, text="Infinite mode", variable=self.var_infinite).grid(row=3, column=1, sticky="w")

        tk.Button(frm2, text="Start Sending", command=self.thread_send).grid(row=4, column=0, pady=6)
        tk.Button(frm2, text="Stop", command=self.bot.stop).grid(row=4, column=1, pady=6)

        # Status box
        self.status_box = scrolledtext.ScrolledText(root, height=10)
        self.status_box.pack(padx=8, pady=6, fill="both")

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def add_status(self, text):
        ts = time.strftime("%H:%M:%S")
        self.status_box.insert("end", f"[{ts}] {text}\n")
        self.status_box.see("end")

    def thread_login(self):
        threading.Thread(target=self.do_login, daemon=True).start()

    def do_login(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()
        login_url = self.login_url.get().strip()
        sel_display = self.sel_display.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Missing", "Nhập username và password")
            return
        self.bot.login(login_url, user, pwd,
                       username_selector="input#login-username",
                       password_selector="input#login-password",
                       submit_selector="button#login-button",
                       username_display_selector=sel_display)
        # Khối thông báo lỗi đã được xóa khỏi đây

    def thread_send(self):
        threading.Thread(target=self.do_send, daemon=True).start()

    def do_send(self):
        try:
            add_sel = self.sel_add.get().strip()
            how = int(self.how_many.get().strip())
            id_min = int(self.id_min.get().strip())
            id_max = int(self.id_max.get().strip())
            infinite = self.var_infinite.get()
            self.bot.send_friend_request_by_id(add_button_selector=add_sel, how_many=how,
                                               delay_between=2, id_min=id_min, id_max=id_max,
                                               infinite=infinite)
        except Exception as e:
            self.add_status(f"Error starting send: {e}")

    def thread_unfriend(self):
        threading.Thread(target=self.do_unfriend, daemon=True).start()

    def on_close(self):
        try:
            self.bot.close()
        finally:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()