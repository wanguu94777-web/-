# -*- coding: utf-8 -*-
"""
RPG Maker MV / MZ JSON 視覺化翻譯工具 (GUI)
基於 Tkinter 開發，提供友善的操作介面與多執行緒無凍結翻譯體驗。
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from rpg_translator_core import RPGProjectManager

class RPGTranslatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RPG Maker MV / MZ JSON 遊戲翻譯神器 v1.0")
        self.root.geometry("780x680")
        self.root.minsize(680, 580)

        # 設定風格
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.project_mgr = None
        self.is_running = False
        self.stop_requested = False

        self._build_ui()

    def _build_ui(self):
        # 頂部標題說明
        top_frame = ttk.Frame(self.root, padding=12)
        top_frame.pack(fill=tk.X)
        title_label = ttk.Label(
            top_frame,
            text="RPG Maker MV / MZ 專用 JSON 翻譯工具",
            font=("Microsoft JhengHei UI", 16, "bold")
        )
        title_label.pack(anchor=tk.W)
        sub_label = ttk.Label(
            top_frame,
            text="安全翻譯遊戲對話、選單、資料庫與道具，智慧保護 \\C[n] \\V[n] 控制碼與外掛標籤，支援一鍵備份與匯出匯入。",
            font=("Microsoft JhengHei UI", 9),
            foreground="#555555"
        )
        sub_label.pack(anchor=tk.W, pady=(2, 0))

        # 主設定卡片 (LabelFrame)
        config_frame = ttk.LabelFrame(self.root, text=" 專案與翻譯設定 ", padding=12)
        config_frame.pack(fill=tk.X, padx=12, pady=6)

        # 1. 遊戲 data 資料夾選擇
        dir_frame = ttk.Frame(config_frame)
        dir_frame.pack(fill=tk.X, pady=4)
        ttk.Label(dir_frame, text="遊戲 data 資料夾:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.data_dir_var = tk.StringVar()
        self.data_dir_entry = ttk.Entry(dir_frame, textvariable=self.data_dir_var)
        self.data_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 6))
        browse_btn = ttk.Button(dir_frame, text="瀏覽選擇...", command=self._browse_folder)
        browse_btn.pack(side=tk.LEFT)

        # 2. 語言設定
        lang_frame = ttk.Frame(config_frame)
        lang_frame.pack(fill=tk.X, pady=4)
        ttk.Label(lang_frame, text="原始語言 (來源):", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.src_lang_var = tk.StringVar(value="ja")
        src_combo = ttk.Combobox(lang_frame, textvariable=self.src_lang_var, values=["ja (日文)", "en (英文)", "auto (自動偵測)"], width=15, state="readonly")
        src_combo.pack(side=tk.LEFT, padx=(4, 20))
        src_combo.current(0)

        ttk.Label(lang_frame, text="目標語言:").pack(side=tk.LEFT)
        self.tgt_lang_var = tk.StringVar(value="zh-TW")
        tgt_combo = ttk.Combobox(lang_frame, textvariable=self.tgt_lang_var, values=["zh-TW (繁體中文)", "zh-CN (簡體中文)", "en (英文)"], width=16, state="readonly")
        tgt_combo.pack(side=tk.LEFT, padx=(4, 0))
        tgt_combo.current(0)

        # 3. 翻譯引擎選擇
        engine_frame = ttk.Frame(config_frame)
        engine_frame.pack(fill=tk.X, pady=4)
        ttk.Label(engine_frame, text="翻譯引擎:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.engine_var = tk.StringVar(value="google")
        r0 = ttk.Radiobutton(engine_frame, text="Google 翻譯 (免費、免 Key - 推薦首選)", variable=self.engine_var, value="google", command=self._on_engine_change)
        r0.pack(side=tk.LEFT, padx=(4, 12))
        r1 = ttk.Radiobutton(engine_frame, text="Claude (Anthropic API - 需 Key)", variable=self.engine_var, value="claude", command=self._on_engine_change)
        r1.pack(side=tk.LEFT, padx=(0, 12))
        r2 = ttk.Radiobutton(engine_frame, text="OpenAI / 其他相容", variable=self.engine_var, value="openai", command=self._on_engine_change)
        r2.pack(side=tk.LEFT)

        # 4. LLM / Claude 進階設定 (可摺疊/動態顯示)
        self.llm_frame = ttk.Frame(config_frame)
        
        llm_row1 = ttk.Frame(self.llm_frame)
        llm_row1.pack(fill=tk.X, pady=2)
        self.api_key_label = ttk.Label(llm_row1, text="Claude API Key:", width=16, anchor=tk.W)
        self.api_key_label.pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        ttk.Entry(llm_row1, textvariable=self.api_key_var, show="*").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        llm_row2 = ttk.Frame(self.llm_frame)
        llm_row2.pack(fill=tk.X, pady=2)
        ttk.Label(llm_row2, text="Base URL:", width=16, anchor=tk.W).pack(side=tk.LEFT)
        self.base_url_var = tk.StringVar(value="https://api.anthropic.com/v1")
        ttk.Entry(llm_row2, textvariable=self.base_url_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 20))

        ttk.Label(llm_row2, text="Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="claude-3-5-haiku-20241022")
        self.model_combo = ttk.Combobox(
            llm_row2,
            textvariable=self.model_var,
            values=["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
            width=26
        )
        self.model_combo.pack(side=tk.LEFT, padx=(4, 0))

        # 功能按鈕卡片
        btn_frame = ttk.Frame(self.root, padding=12)
        btn_frame.pack(fill=tk.X)

        self.start_btn = tk.Button(
            btn_frame,
            text="🚀 一鍵自動翻譯遊戲",
            font=("Microsoft JhengHei UI", 11, "bold"),
            bg="#2563EB",
            fg="white",
            padx=16,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
            command=self._start_auto_translate
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_btn = ttk.Button(btn_frame, text="💾 匯出待翻譯文本 (JSON)", command=self._export_json)
        self.export_btn.pack(side=tk.LEFT, padx=4)

        self.import_btn = ttk.Button(btn_frame, text="📥 匯入已翻譯文本 (JSON)", command=self._import_json)
        self.import_btn.pack(side=tk.LEFT, padx=4)

        self.restore_btn = ttk.Button(btn_frame, text="🔄 還原備份", command=self._restore_backup)
        self.restore_btn.pack(side=tk.LEFT, padx=4)

        self.clear_cache_btn = ttk.Button(btn_frame, text="🧹 清除快取", command=self._clear_cache)
        self.clear_cache_btn.pack(side=tk.LEFT, padx=4)

        self.stop_btn = ttk.Button(btn_frame, text="⏹ 停止", state=tk.DISABLED, command=self._request_stop)
        self.stop_btn.pack(side=tk.RIGHT)

        # 進度條與狀態列
        progress_box = ttk.Frame(self.root, padding=(12, 0, 12, 6))
        progress_box.pack(fill=tk.X)
        self.status_var = tk.StringVar(value="狀態: 就緒。請選擇遊戲的 data 資料夾。")
        self.status_label = ttk.Label(progress_box, textvariable=self.status_var, font=("Microsoft JhengHei UI", 9))
        self.status_label.pack(anchor=tk.W, pady=(0, 2))

        self.progress_bar = ttk.Progressbar(progress_box, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        # 日誌輸出視窗
        log_frame = ttk.LabelFrame(self.root, text=" 執行日誌與即時訊息 ", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="white"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self._log("歡迎使用 RPG Maker MV / MZ JSON 翻譯工具！")
        self._log("提示: RPG Maker MV 通常位於 www/data/，MZ 通常位於 data/。")

    def _log(self, message: str):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def _on_engine_change(self):
        engine = self.engine_var.get()
        if engine == "claude":
            self.llm_frame.pack(fill=tk.X, pady=(6, 2))
            self.api_key_label.config(text="Claude API Key:")
            self.base_url_var.set("https://api.anthropic.com/v1")
            self.model_combo.config(values=["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"])
            self.model_var.set("claude-3-5-haiku-20241022")
        elif engine == "openai":
            self.llm_frame.pack(fill=tk.X, pady=(6, 2))
            self.api_key_label.config(text="API Key:")
            self.base_url_var.set("https://api.openai.com/v1")
            self.model_combo.config(values=["gpt-4o-mini", "gpt-4o", "deepseek-chat", "gemini-2.0-flash"])
            self.model_var.set("gpt-4o-mini")
        else:
            self.llm_frame.pack_forget()

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="選擇 RPG Maker 的 data 資料夾")
        if folder:
            # 檢查是否為 www 目錄，如果是 www，自動尋找內層 data
            if os.path.basename(folder).lower() == "www" and os.path.isdir(os.path.join(folder, "data")):
                folder = os.path.join(folder, "data")
            # 如果使用者選取遊戲根目錄，自動尋找 www/data 或 data
            elif os.path.isdir(os.path.join(folder, "www", "data")):
                folder = os.path.join(folder, "www", "data")
            elif os.path.isdir(os.path.join(folder, "data")):
                folder = os.path.join(folder, "data")

            self.data_dir_var.set(folder)
            self._init_project()

    def _init_project(self) -> bool:
        data_dir = self.data_dir_var.get().strip()
        if not data_dir or not os.path.isdir(data_dir):
            messagebox.showerror("錯誤", "請先選擇有效的 RPG Maker data 資料夾！")
            return False
        self.project_mgr = RPGProjectManager(data_dir)
        files = self.project_mgr.get_json_files()
        if not files:
            self._log(f"[警告] 資料夾 {data_dir} 內未發現 RPG Maker 相關 JSON 檔案！")
            messagebox.showwarning("提示", "此資料夾內沒有找到 Actors.json、MapXXX.json 等 RPG Maker 檔案，請確認是否選錯資料夾。")
            return False
        self._log(f"[已就緒] 成功載入專案！發現 {len(files)} 個 RPG Maker JSON 資料檔。")
        self.status_var.set(f"就緒: 找到 {len(files)} 個遊戲資料檔案。")
        return True

    def _set_ui_state(self, running: bool):
        self.is_running = running
        state = tk.DISABLED if running else tk.NORMAL
        self.start_btn.config(state=state)
        self.export_btn.config(state=state)
        self.import_btn.config(state=state)
        self.restore_btn.config(state=state)
        self.clear_cache_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if running else tk.DISABLED)

    def _request_stop(self):
        if self.is_running:
            self.stop_requested = True
            self._log("[使用者請求停止] 正在安全停止翻譯...")

    def _start_auto_translate(self):
        if not self._init_project():
            return

        engine = self.engine_var.get()
        api_key = self.api_key_var.get().strip()

        # 檢查 API Key 避免 401 錯誤
        if engine in ["claude", "openai"] and not api_key:
            messagebox.showwarning(
                "缺少 API Key",
                f"您選擇了 {engine.upper()} 翻譯引擎，但尚未填寫 API Key！\n\n"
                "• 若您沒有 API Key，請將上方翻譯引擎切換為「Google 翻譯 (免費、免 Key)」！\n"
                "• 若您有 API Key，請在設定欄位填入後再點擊開始。"
            )
            return

        # 確認對話框
        if not messagebox.askyesno("確認開始翻譯", "即將開始自動翻譯，系統會先自動建立完整備份。\n是否繼續？"):
            return

        self._set_ui_state(True)
        self.stop_requested = False

        # 取得參數
        src = self.src_lang_var.get().split()[0]
        tgt = self.tgt_lang_var.get().split()[0]
        base_url = self.base_url_var.get().strip()
        model = self.model_var.get().strip()

        def worker():
            try:
                # 1. 建立自動備份
                self._log("[步驟 1/3] 正在建立安全備份...")
                backup_path = self.project_mgr.create_backup()
                self._log(f"[備份成功] 備份存放於: {backup_path}")

                # 2. 自動翻譯
                self._log(f"[步驟 2/3] 開始翻譯流程 (引擎: {engine}, 來源: {src}, 目標: {tgt})...")
                
                def progress(current, total, msg):
                    self.root.after(0, lambda: self._update_progress(current, total, msg))

                self.project_mgr.auto_translate(
                    engine_type=engine,
                    src_lang=src,
                    tgt_lang=tgt,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    progress_cb=progress,
                    stop_check=lambda: self.stop_requested
                )

                if self.stop_requested:
                    self._log("[已終止] 翻譯已手動停止。已翻譯的項目已妥善儲存至快取中。")
                    self.root.after(0, lambda: messagebox.showinfo("已停止", "翻譯已停止，下次啟動時會從中斷處繼續！"))
                else:
                    self._log("[完成] 🎉 恭喜！所有 RPG Maker 文本翻譯並回填完畢！")
                    self.root.after(0, lambda: messagebox.showinfo("成功", "遊戲翻譯完成！可以啟動遊戲測試囉！"))

            except Exception as e:
                self._log(f"[錯誤] 發生異常: {e}")
                self.root.after(0, lambda: messagebox.showerror("發生錯誤", f"翻譯過程發生錯誤:\n{e}"))
            finally:
                self.root.after(0, lambda: self._set_ui_state(False))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, current, total, msg):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar['value'] = pct
            self.status_var.set(f"[{pct}%] {msg}")
        else:
            self.status_var.set(msg)
        self._log(f"-> {msg}")

    def _export_json(self):
        if not self._init_project():
            return
        out_file = filedialog.asksaveasfilename(
            title="儲存待翻譯 JSON 檔案",
            defaultextension=".json",
            filetypes=[("JSON 檔案", "*.json")]
        )
        if not out_file:
            return
        try:
            self._log(f"正在掃描並匯出文本至: {out_file} ...")
            self.project_mgr.export_to_json(out_file)
            self._log(f"[匯出成功] 文本已成功匯出至: {out_file}")
            messagebox.showinfo("匯出成功", f"文本已匯出至:\n{out_file}\n您可以使用任何文本編輯器、Excel 或 AI 進行批次翻譯！")
        except Exception as e:
            messagebox.showerror("匯出失敗", str(e))

    def _import_json(self):
        if not self._init_project():
            return
        in_file = filedialog.askopenfilename(
            title="選擇已翻譯的 JSON 檔案",
            filetypes=[("JSON 檔案", "*.json")]
        )
        if not in_file:
            return

        if not messagebox.askyesno("確認匯入", f"即將將 {os.path.basename(in_file)} 的翻譯內容寫回遊戲檔案中。\n是否繼續？"):
            return

        self._set_ui_state(True)

        def worker():
            try:
                # 建立備份
                self._log("[步驟 1/2] 建立安全備份...")
                bk = self.project_mgr.create_backup()
                self._log(f"[備份成功] 備份存放於: {bk}")

                # 匯入寫回
                self._log(f"[步驟 2/2] 正在套用翻譯: {in_file} ...")
                def progress(current, total, msg):
                    self.root.after(0, lambda: self._update_progress(current, total, msg))

                self.project_mgr.import_from_json(in_file, progress_cb=progress)
                self._log("[完成] 翻譯已成功套用至遊戲資料中！")
                self.root.after(0, lambda: messagebox.showinfo("成功", "已成功將翻譯回填至遊戲中！"))
            except Exception as e:
                self._log(f"[錯誤] 匯入失敗: {e}")
                self.root.after(0, lambda: messagebox.showerror("匯入失敗", str(e)))
            finally:
                self.root.after(0, lambda: self._set_ui_state(False))

        threading.Thread(target=worker, daemon=True).start()

    def _restore_backup(self):
        if not self._init_project():
            return
        folder = filedialog.askdirectory(title="選擇要還原的 data_backup_XXX 資料夾")
        if not folder:
            return
        if not messagebox.askyesno("確認還原", f"確定要將遊戲資料還原至此備份嗎？\n{folder}"):
            return
        try:
            self.project_mgr.restore_backup(folder)
            self._log(f"[還原成功] 已還原備份: {folder}")
            messagebox.showinfo("還原成功", "遊戲資料已成功還原！")
        except Exception as e:
            messagebox.showerror("還原失敗", str(e))

    def _clear_cache(self):
        if not self._init_project():
            return
        if not messagebox.askyesno("確認清除快取", "確定要清除先前儲存的翻譯快取嗎？\n\n這會清除先前 401 錯誤或中斷留下的快取紀錄，以便重新進行完整翻譯。"):
            return
        try:
            self.project_mgr.clear_cache()
            self._log("[快取已清除] 已清空 translation_cache.json。")
            messagebox.showinfo("完成", "已成功清除翻譯快取！現在可以重新點擊「一鍵自動翻譯遊戲」。")
        except Exception as e:
            messagebox.showerror("清除失敗", str(e))

def main():
    root = tk.Tk()
    app = RPGTranslatorApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
