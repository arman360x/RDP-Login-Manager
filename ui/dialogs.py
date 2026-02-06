import json
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.encryption import encrypt_password, decrypt_password
from core import database as db


class ConnectionDialog(ctk.CTkToplevel):
    def __init__(self, parent, master_password: str, encryption_salt: bytes,
                 connection: dict = None, categories: list = None):
        super().__init__(parent)
        self.result = None
        self.master_password = master_password
        self.encryption_salt = encryption_salt
        self.connection = connection
        self.categories = categories or []

        is_edit = connection is not None
        self.title("Edit Connection" if is_edit else "Add Connection")
        self.geometry("500x620")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(scroll, text="Connection Name *", anchor="w").pack(fill="x")
        self.name_entry = ctk.CTkEntry(scroll, height=32)
        self.name_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(scroll, text="Hostname / IP *", anchor="w").pack(fill="x")
        self.host_entry = ctk.CTkEntry(scroll, height=32)
        self.host_entry.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 8))
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=(0, 5))
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="left", fill="x", expand=True, padx=(5, 0))

        ctk.CTkLabel(left, text="Port", anchor="w").pack(fill="x")
        self.port_entry = ctk.CTkEntry(left, height=32)
        self.port_entry.pack(fill="x")
        self.port_entry.insert(0, "3389")

        ctk.CTkLabel(right, text="Category", anchor="w").pack(fill="x")
        cat_names = ["(None)"] + [c["name"] for c in self.categories]
        self.category_var = ctk.StringVar(value="(None)")
        self.category_menu = ctk.CTkOptionMenu(right, values=cat_names, variable=self.category_var, height=32)
        self.category_menu.pack(fill="x")

        ctk.CTkLabel(scroll, text="Username", anchor="w").pack(fill="x")
        self.user_entry = ctk.CTkEntry(scroll, height=32)
        self.user_entry.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(scroll, text="Password", anchor="w").pack(fill="x")
        pass_row = ctk.CTkFrame(scroll, fg_color="transparent")
        pass_row.pack(fill="x", pady=(0, 8))
        self.pass_entry = ctk.CTkEntry(pass_row, show="*", height=32)
        self.pass_entry.pack(side="left", fill="x", expand=True)
        self._pass_visible = False
        self._pass_toggle = ctk.CTkButton(
            pass_row, text="Show", width=55, height=32,
            fg_color=("gray70", "gray35"), hover_color=("gray60", "gray45"),
            command=self._toggle_conn_password,
        )
        self._pass_toggle.pack(side="left", padx=(5, 0))

        # RDP Settings
        ctk.CTkLabel(scroll, text="RDP Settings", font=ctk.CTkFont(weight="bold")).pack(
            fill="x", pady=(10, 5)
        )

        row2 = ctk.CTkFrame(scroll, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 8))

        sm_frame = ctk.CTkFrame(row2, fg_color="transparent")
        sm_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkLabel(sm_frame, text="Screen Mode", anchor="w").pack(fill="x")
        self.screen_mode_var = ctk.StringVar(value="Fullscreen")
        ctk.CTkOptionMenu(sm_frame, values=["Fullscreen", "Windowed"], variable=self.screen_mode_var, height=32).pack(fill="x")

        cd_frame = ctk.CTkFrame(row2, fg_color="transparent")
        cd_frame.pack(side="left", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(cd_frame, text="Color Depth", anchor="w").pack(fill="x")
        self.color_depth_var = ctk.StringVar(value="32")
        ctk.CTkOptionMenu(cd_frame, values=["15", "16", "24", "32"], variable=self.color_depth_var, height=32).pack(fill="x")

        row3 = ctk.CTkFrame(scroll, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 8))

        w_frame = ctk.CTkFrame(row3, fg_color="transparent")
        w_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkLabel(w_frame, text="Width", anchor="w").pack(fill="x")
        self.width_entry = ctk.CTkEntry(w_frame, height=32)
        self.width_entry.pack(fill="x")
        self.width_entry.insert(0, "1920")

        h_frame = ctk.CTkFrame(row3, fg_color="transparent")
        h_frame.pack(side="left", fill="x", expand=True, padx=(5, 0))
        ctk.CTkLabel(h_frame, text="Height", anchor="w").pack(fill="x")
        self.height_entry = ctk.CTkEntry(h_frame, height=32)
        self.height_entry.pack(fill="x")
        self.height_entry.insert(0, "1080")

        self.clipboard_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(scroll, text="Redirect Clipboard", variable=self.clipboard_var).pack(
            fill="x", pady=2
        )
        self.printers_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(scroll, text="Redirect Printers", variable=self.printers_var).pack(
            fill="x", pady=2
        )
        self.drives_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(scroll, text="Redirect Drives", variable=self.drives_var).pack(
            fill="x", pady=2
        )

        ctk.CTkLabel(scroll, text="Notes", anchor="w").pack(fill="x", pady=(8, 0))
        self.notes_text = ctk.CTkTextbox(scroll, height=60)
        self.notes_text.pack(fill="x", pady=(0, 10))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="Save", command=self._on_save, width=100).pack(side="right")
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=80, fg_color="gray").pack(
            side="right", padx=(0, 10)
        )

        if is_edit:
            self._populate(connection)

    def _toggle_conn_password(self):
        self._pass_visible = not self._pass_visible
        self.pass_entry.configure(show="" if self._pass_visible else "*")
        self._pass_toggle.configure(text="Hide" if self._pass_visible else "Show")

    def _populate(self, c: dict):
        self.name_entry.insert(0, c.get("name", ""))
        self.host_entry.insert(0, c.get("hostname", ""))
        self.port_entry.delete(0, "end")
        self.port_entry.insert(0, str(c.get("port", 3389)))
        self.user_entry.insert(0, c.get("username", ""))

        if c.get("encrypted_password"):
            try:
                plain = decrypt_password(c["encrypted_password"], self.master_password, self.encryption_salt)
                self.pass_entry.insert(0, plain)
            except Exception:
                pass

        cat_id = c.get("category_id")
        if cat_id:
            cat = next((cat for cat in self.categories if cat["id"] == cat_id), None)
            if cat:
                self.category_var.set(cat["name"])

        self.screen_mode_var.set("Fullscreen" if c.get("screen_mode", 2) == 2 else "Windowed")
        self.color_depth_var.set(str(c.get("color_depth", 32)))
        self.width_entry.delete(0, "end")
        self.width_entry.insert(0, str(c.get("desktop_width", 1920)))
        self.height_entry.delete(0, "end")
        self.height_entry.insert(0, str(c.get("desktop_height", 1080)))
        self.clipboard_var.set(bool(c.get("redirect_clipboard", 1)))
        self.printers_var.set(bool(c.get("redirect_printers", 0)))
        self.drives_var.set(bool(c.get("redirect_drives", 0)))
        self.notes_text.insert("1.0", c.get("notes", ""))

    def _on_save(self):
        name = self.name_entry.get().strip()
        hostname = self.host_entry.get().strip()
        if not name or not hostname:
            messagebox.showwarning("Validation", "Name and Hostname are required.", parent=self)
            return

        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showwarning("Validation", "Port must be a number.", parent=self)
            return

        password = self.pass_entry.get()
        enc_pass = ""
        if password:
            enc_pass = encrypt_password(password, self.master_password, self.encryption_salt)

        cat_name = self.category_var.get()
        cat_id = None
        if cat_name != "(None)":
            cat = next((c for c in self.categories if c["name"] == cat_name), None)
            if cat:
                cat_id = cat["id"]

        self.result = {
            "name": name,
            "hostname": hostname,
            "port": port,
            "username": self.user_entry.get().strip(),
            "encrypted_password": enc_pass,
            "category_id": cat_id,
            "screen_mode": 2 if self.screen_mode_var.get() == "Fullscreen" else 1,
            "desktop_width": int(self.width_entry.get() or 1920),
            "desktop_height": int(self.height_entry.get() or 1080),
            "color_depth": int(self.color_depth_var.get()),
            "redirect_clipboard": int(self.clipboard_var.get()),
            "redirect_printers": int(self.printers_var.get()),
            "redirect_drives": int(self.drives_var.get()),
            "notes": self.notes_text.get("1.0", "end-1c").strip(),
        }
        self.grab_release()
        self.destroy()


class CategoryDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_name: str = ""):
        super().__init__(parent)
        self.result = None

        is_edit = bool(current_name)
        self.title("Rename Category" if is_edit else "Add Category")
        self.geometry("350x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(frame, text="Category Name:", anchor="w").pack(fill="x")
        self.name_entry = ctk.CTkEntry(frame, height=35)
        self.name_entry.pack(fill="x", pady=(0, 10))
        self.name_entry.insert(0, current_name)
        self.name_entry.focus_set()
        self.name_entry.bind("<Return>", lambda e: self._on_save())

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="Save", command=self._on_save, width=80).pack(side="right")
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=80, fg_color="gray").pack(
            side="right", padx=(0, 10)
        )

    def _on_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Name cannot be empty.", parent=self)
            return
        self.result = name
        self.grab_release()
        self.destroy()


class ImportExportDialog(ctk.CTkToplevel):
    def __init__(self, parent, mode: str = "export"):
        super().__init__(parent)
        self.result = None
        self.mode = mode

        self.title("Export Connections" if mode == "export" else "Import Connections")
        self.geometry("400x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        if mode == "export":
            ctk.CTkLabel(frame, text="Export all connections to a JSON file.").pack(pady=(0, 10))
            ctk.CTkButton(frame, text="Choose File & Export", command=self._do_export).pack()
        else:
            ctk.CTkLabel(frame, text="Import connections from a JSON file.").pack(pady=(0, 10))
            ctk.CTkLabel(frame, text="Existing connections will not be overwritten.", font=ctk.CTkFont(size=11)).pack(pady=(0, 10))
            ctk.CTkButton(frame, text="Choose File & Import", command=self._do_import).pack()

    def _do_export(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export Connections",
        )
        if path:
            data = db.export_connections()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            messagebox.showinfo("Export", f"Exported {len(data.get('connections', []))} connections.", parent=self)
            self.result = path
            self.grab_release()
            self.destroy()

    def _do_import(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("JSON files", "*.json")],
            title="Import Connections",
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                db.import_connections(data)
                count = len(data.get("connections", []))
                messagebox.showinfo("Import", f"Imported {count} connections.", parent=self)
                self.result = path
                self.grab_release()
                self.destroy()
            except Exception as e:
                messagebox.showerror("Import Error", str(e), parent=self)
