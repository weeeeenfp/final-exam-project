"""
gui.py - 名言佳句管理系統 (Tkinter GUI)

提供使用者介面，透過多執行緒 (Threading) 呼叫後端 API，
實現不卡頓的 CRUD 操作體驗。
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Dict, Any, List

import requests

# --- 常數設定 ---
API_BASE_URL = "http://127.0.0.1:8000/quotes"
REQUEST_TIMEOUT = 5  # 網路請求超時設定 (秒)


class QuoteApp:
    """名言佳句管理應用程式主類別"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("名言佳句管理系統 (專業版)")
        self.root.geometry("800x600")

        # 狀態變數
        self.selected_id = None

        # 初始化介面
        self._setup_ui()

        # 啟動時載入資料
        self.refresh_data()

    def _setup_ui(self) -> None:
        """配置視窗元件佈局"""
        # 1. 資料列表區 (Treeview)
        frame_top = tk.Frame(self.root)
        frame_top.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("ID", "Author", "Text", "Tags")
        self.tree = ttk.Treeview(frame_top, columns=columns, show="headings")

        # 設定欄位
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.heading("Author", text="作者")
        self.tree.column("Author", width=150)
        self.tree.heading("Text", text="名言內容")
        self.tree.column("Text", width=400)
        self.tree.heading("Tags", text="標籤")
        self.tree.column("Tags", width=150)

        scrollbar = ttk.Scrollbar(frame_top, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # 2. 編輯區
        frame_mid = tk.LabelFrame(self.root, text="編輯/新增區")
        frame_mid.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame_mid, text="名言內容 (Text):").pack(anchor="w", padx=5)
        self.text_content = tk.Text(frame_mid, height=5)
        self.text_content.pack(fill=tk.X, padx=5, pady=2)

        frame_inputs = tk.Frame(frame_mid)
        frame_inputs.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(frame_inputs, text="作者 (Author):").grid(row=0, column=0, sticky="w")
        self.entry_author = tk.Entry(frame_inputs, width=30)
        self.entry_author.grid(row=1, column=0, padx=(0, 20), sticky="w")

        tk.Label(frame_inputs, text="標籤 (Tags):").grid(row=0, column=1, sticky="w")
        self.entry_tags = tk.Entry(frame_inputs, width=30)
        self.entry_tags.grid(row=1, column=1, sticky="w")

        # 3. 按鈕區
        frame_btn = tk.LabelFrame(self.root, text="操作選項")
        frame_btn.pack(fill=tk.X, padx=10, pady=5)

        self.btn_refresh = tk.Button(frame_btn, text="重新整理", bg="lightblue", command=self.refresh_data)
        self.btn_refresh.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_add = tk.Button(frame_btn, text="新增", bg="lightgreen", command=self.add_data)
        self.btn_add.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_update = tk.Button(frame_btn, text="更新", bg="orange", state=tk.DISABLED, command=self.update_data)
        self.btn_update.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_delete = tk.Button(frame_btn, text="刪除", bg="salmon", state=tk.DISABLED, command=self.delete_data)
        self.btn_delete.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # 4. 狀態列
        self.status_var = tk.StringVar(value="準備就緒")
        self.status_label = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    # --- UI 邏輯 ---

    def _set_status(self, msg: str, is_error: bool = False) -> None:
        """更新狀態列文字顏色"""
        self.status_var.set(msg)
        self.status_label.config(fg="red" if is_error else "black")

    def _toggle_inputs(self, enable: bool) -> None:
        """鎖定或解鎖介面，防止重複操作"""
        state = tk.NORMAL if enable else tk.DISABLED
        self.btn_refresh.config(state=state)
        self.btn_add.config(state=state)
        # 更新與刪除按鈕需視是否有選取項目決定
        if enable and self.selected_id:
            self.btn_update.config(state=tk.NORMAL)
            self.btn_delete.config(state=tk.NORMAL)
        else:
            self.btn_update.config(state=tk.DISABLED)
            self.btn_delete.config(state=tk.DISABLED)

    def _on_tree_select(self, event) -> None:
        """處理列表點擊事件"""
        selected_item = self.tree.selection()
        if not selected_item:
            return

        values = self.tree.item(selected_item[0], "values")
        if values:
            self.selected_id = values[0]
            # 填入資料
            self.entry_author.delete(0, tk.END)
            self.entry_author.insert(0, values[1])
            self.text_content.delete("1.0", tk.END)
            self.text_content.insert("1.0", values[2])
            self.entry_tags.delete(0, tk.END)
            self.entry_tags.insert(0, values[3])

            self.btn_update.config(state=tk.NORMAL)
            self.btn_delete.config(state=tk.NORMAL)
            self._set_status(f"已選取 ID: {self.selected_id}")

    # --- 功能實作 (Threading Pattern) ---

    def refresh_data(self) -> None:
        self._set_status("資料載入中...")
        self._toggle_inputs(False)
        threading.Thread(target=self._worker_get_quotes, daemon=True).start()

    def _worker_get_quotes(self) -> None:
        try:
            response = requests.get(API_BASE_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()  # 若 4xx/5xx 會拋出例外
            data = response.json()
            self.root.after(0, lambda: self._ui_refresh_success(data))
        except requests.RequestException as e:
            self.root.after(0, lambda: self._ui_error(f"連線失敗: {e}"))

    def _ui_refresh_success(self, data: List[Dict]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for quote in data:
            self.tree.insert("", tk.END, values=(quote['id'], quote['author'], quote['text'], quote['tags']))

        self._set_status(f"載入完成，共 {len(data)} 筆")
        self.selected_id = None
        self._toggle_inputs(True)

    def add_data(self) -> None:
        payload = {
            "text": self.text_content.get("1.0", "end-1c").strip(),
            "author": self.entry_author.get().strip(),
            "tags": self.entry_tags.get().strip()
        }
        if not payload["text"] or not payload["author"]:
            messagebox.showwarning("警告", "內容與作者不得為空")
            return

        self._set_status("新增資料中...")
        self._toggle_inputs(False)
        threading.Thread(target=self._worker_post_quote, args=(payload,), daemon=True).start()

    def _worker_post_quote(self, payload: Dict[str, Any]) -> None:
        try:
            response = requests.post(API_BASE_URL, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            self.root.after(0, self._ui_action_success, "新增成功")
        except requests.RequestException as e:
            self.root.after(0, lambda: self._ui_error(f"新增失敗: {e}"))

    def update_data(self) -> None:
        if not self.selected_id:
            return

        payload = {
            "text": self.text_content.get("1.0", "end-1c").strip(),
            "author": self.entry_author.get().strip(),
            "tags": self.entry_tags.get().strip()
        }

        self._set_status("更新資料中...")
        self._toggle_inputs(False)
        threading.Thread(target=self._worker_put_quote, args=(self.selected_id, payload), daemon=True).start()

    def _worker_put_quote(self, quote_id: str, payload: Dict[str, Any]) -> None:
        try:
            url = f"{API_BASE_URL}/{quote_id}"
            response = requests.put(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            self.root.after(0, self._ui_action_success, "更新成功")
        except requests.RequestException as e:
            self.root.after(0, lambda: self._ui_error(f"更新失敗: {e}"))

    def delete_data(self) -> None:
        if not self.selected_id:
            return
        if not messagebox.askyesno("確認", f"確定刪除 ID {self.selected_id}？"):
            return

        self._set_status("刪除資料中...")
        self._toggle_inputs(False)
        threading.Thread(target=self._worker_delete_quote, args=(self.selected_id,), daemon=True).start()

    def _worker_delete_quote(self, quote_id: str) -> None:
        try:
            url = f"{API_BASE_URL}/{quote_id}"
            response = requests.delete(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            self.root.after(0, self._ui_action_success, "刪除成功")
        except requests.RequestException as e:
            self.root.after(0, lambda: self._ui_error(f"刪除失敗: {e}"))

    # --- 通用回調 ---
    def _ui_action_success(self, msg: str) -> None:
        """新增/修改/刪除成功後的通用處理"""
        self._set_status(msg)
        # 清空輸入
        self.entry_author.delete(0, tk.END)
        self.entry_tags.delete(0, tk.END)
        self.text_content.delete("1.0", tk.END)
        # 重新載入列表
        self.refresh_data()

    def _ui_error(self, error_msg: str) -> None:
        """發生錯誤時的通用處理"""
        self._set_status("操作失敗", is_error=True)
        self._toggle_inputs(True)
        messagebox.showerror("錯誤", error_msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = QuoteApp(root)
    root.mainloop()