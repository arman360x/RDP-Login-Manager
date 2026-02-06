import base64
import json
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from core import database as db
from core.encryption import generate_salt, DEFAULT_PASSPHRASE
from core.rdp import connect as rdp_connect
from ui.sidebar import Sidebar
from ui.details import DetailsPanel
from ui.dialogs import (
    ConnectionDialog,
    CategoryDialog,
    ImportExportDialog,
)

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
ASSETS_PATH = Path(__file__).parent.parent / "assets"


def load_config() -> dict:
    defaults = {
        "clear_credentials_on_close": True,
        "default_port": 3389,
        "default_screen_mode": 2,
    }
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
            defaults.update(data)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return defaults


class RDPManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RDP Manager")
        self.geometry("1100x700")
        self.minsize(800, 500)

        ico_path = ASSETS_PATH / "logo.ico"
        if ico_path.exists():
            self.iconbitmap(str(ico_path))

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config = load_config()
        self.master_password = DEFAULT_PASSPHRASE
        self.encryption_salt = None
        self._tray_icon = None

        db.init_db()
        self._init_encryption_salt()
        self._build_ui()
        self._setup_tray()

    def _init_encryption_salt(self):
        salt_b64 = db.get_setting("encryption_salt")
        if salt_b64:
            self.encryption_salt = base64.b64decode(salt_b64)
        else:
            self.encryption_salt = generate_salt()
            db.set_setting("encryption_salt", base64.b64encode(self.encryption_salt).decode())

    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, height=50, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search())
        search = ctk.CTkEntry(
            top, placeholder_text="Search connections...",
            textvariable=self.search_var, width=250, height=32,
        )
        search.pack(side="left", padx=(15, 10), pady=9)

        # Category filter
        self._cat_filter_var = ctk.StringVar(value="All Categories")
        self._cat_filter_menu = ctk.CTkOptionMenu(
            top, variable=self._cat_filter_var,
            values=self._get_cat_filter_values(), height=32, width=180,
            command=lambda v: self._on_search(),
        )
        self._cat_filter_menu.pack(side="left", padx=(0, 10), pady=9)

        ctk.CTkButton(
            top, text="+ Connection", width=130, height=32,
            command=self._add_connection,
        ).pack(side="right", padx=(5, 15), pady=9)

        ctk.CTkButton(
            top, text="+ Category", width=110, height=32,
            fg_color=("gray70", "gray35"), hover_color=("gray60", "gray45"),
            command=self._add_category,
        ).pack(side="right", padx=5, pady=9)

        # Menu buttons
        menu_frame = ctk.CTkFrame(top, fg_color="transparent")
        menu_frame.pack(side="right", padx=5)
        ctk.CTkButton(
            menu_frame, text="Import", width=70, height=28,
            fg_color="transparent", hover_color=("gray75", "gray30"),
            command=lambda: self._import_export("import"),
        ).pack(side="left")
        ctk.CTkButton(
            menu_frame, text="Export", width=70, height=28,
            fg_color="transparent", hover_color=("gray75", "gray30"),
            command=lambda: self._import_export("export"),
        ).pack(side="left")

        # Main area
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True)

        self.sidebar = Sidebar(
            main,
            on_select=self._on_select,
            on_connect=self._connect,
            on_edit=self._edit_connection,
            on_delete=self._delete_connection,
            on_duplicate=self._duplicate_connection,
        )
        self.sidebar.pack(side="left", fill="y", padx=(5, 0), pady=5)

        self.details = DetailsPanel(
            main,
            on_connect=self._connect,
            on_edit=self._edit_connection,
            on_delete=self._delete_connection,
        )
        self.details.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Status bar
        self.status_bar = ctk.CTkLabel(
            self, text="Ready", height=25, anchor="w",
            font=ctk.CTkFont(size=11), text_color="gray",
        )
        self.status_bar.pack(fill="x", padx=10, pady=(0, 5))

        # Keybindings
        self.bind("<Control-n>", lambda e: self._add_connection())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<Return>", lambda e: self._connect_selected())

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.sidebar.refresh()

    def _get_cat_filter_values(self) -> list[str]:
        cats = db.get_categories()
        values = ["All Categories", "Uncategorized"]
        values.extend(c["name"] for c in cats)
        return values

    def _get_category_filter_id(self) -> int | None:
        val = self._cat_filter_var.get()
        if val == "All Categories":
            return -1
        if val == "Uncategorized":
            return 0
        cats = db.get_categories()
        cat = next((c for c in cats if c["name"] == val), None)
        return cat["id"] if cat else -1

    def _on_search(self):
        text = self.search_var.get()
        cat_id = self._get_category_filter_id()
        self.sidebar.refresh(filter_text=text, category_filter=cat_id)

    def _on_select(self, conn_id: int):
        self.details.show_connection(conn_id)

    def _connect(self, conn_id: int):
        conn = db.get_connection_by_id(conn_id)
        if not conn:
            return
        self._set_status(f"Connecting to {conn['name']}...")
        try:
            rdp_connect(conn, self.master_password, self.encryption_salt)
            db.update_last_connected(conn_id)
            self._set_status(f"Launched RDP: {conn['name']}")
            self.details.show_connection(conn_id)
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self._set_status("Connection failed")

    def _connect_selected(self):
        sel = self.sidebar.get_selected_id()
        if sel:
            self._connect(sel)

    def _delete_selected(self):
        sel = self.sidebar.get_selected_id()
        if sel:
            self._delete_connection(sel)

    def _add_connection(self):
        categories = db.get_categories()
        dialog = ConnectionDialog(
            self, self.master_password, self.encryption_salt,
            categories=categories,
        )
        self.wait_window(dialog)
        if dialog.result:
            db.add_connection(**dialog.result)
            self._refresh_all()
            self._set_status("Connection added")

    def _edit_connection(self, conn_id: int):
        conn = db.get_connection_by_id(conn_id)
        if not conn:
            return
        categories = db.get_categories()
        dialog = ConnectionDialog(
            self, self.master_password, self.encryption_salt,
            connection=conn, categories=categories,
        )
        self.wait_window(dialog)
        if dialog.result:
            db.update_connection(conn_id, **dialog.result)
            self._refresh_all()
            self.details.show_connection(conn_id)
            self._set_status("Connection updated")

    def _delete_connection(self, conn_id: int):
        conn = db.get_connection_by_id(conn_id)
        if not conn:
            return
        if messagebox.askyesno("Delete Connection", f"Delete '{conn['name']}'?"):
            db.delete_connection(conn_id)
            self.details.clear()
            self._refresh_all()
            self._set_status("Connection deleted")

    def _duplicate_connection(self, conn_id: int):
        new_id = db.duplicate_connection(conn_id)
        if new_id:
            self._refresh_all()
            self._set_status("Connection duplicated")

    def _add_category(self):
        dialog = CategoryDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            try:
                db.add_category(dialog.result)
                self._refresh_all()
                self._update_cat_filter()
                self._set_status(f"Category '{dialog.result}' added")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _import_export(self, mode: str):
        dialog = ImportExportDialog(self, mode=mode)
        self.wait_window(dialog)
        if dialog.result:
            self._refresh_all()
            self._update_cat_filter()

    def _refresh_all(self):
        text = self.search_var.get()
        cat_id = self._get_category_filter_id()
        self.sidebar.refresh(filter_text=text, category_filter=cat_id)

    def _update_cat_filter(self):
        self._cat_filter_menu.configure(values=self._get_cat_filter_values())

    def _set_status(self, text: str):
        self.status_bar.configure(text=text)

    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image

            tray_path = ASSETS_PATH / "tray.png"
            if tray_path.exists():
                img = Image.open(str(tray_path))
            else:
                img = Image.new("RGB", (64, 64), color="#0078d4")

            def on_show(icon, item):
                self.after(0, self._restore_from_tray)

            def on_quit(icon, item):
                icon.stop()
                self.after(0, self.destroy)

            menu = pystray.Menu(
                pystray.MenuItem("Show", on_show, default=True),
                pystray.MenuItem("Quit", on_quit),
            )
            self._tray_icon = pystray.Icon("RDPManager", img, "RDP Manager", menu)

            t = threading.Thread(target=self._tray_icon.run, daemon=True)
            t.start()
        except ImportError:
            pass

    def _restore_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close(self):
        if self._tray_icon:
            self.withdraw()
        else:
            self.destroy()
