import threading
import tkinter as tk
import customtkinter as ctk

from core import database as db
from core.rdp import ping_host


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_select=None, on_connect=None, on_edit=None,
                 on_delete=None, on_duplicate=None):
        super().__init__(parent, width=300)
        self.pack_propagate(False)

        self.on_select = on_select
        self.on_connect = on_connect
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_duplicate = on_duplicate

        self._collapsed = {}
        self._status_cache = {}
        self._widgets = {}
        self._selected_id = None

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="Connect", command=self._ctx_connect)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Edit", command=self._ctx_edit)
        self._context_menu.add_command(label="Duplicate", command=self._ctx_duplicate)
        self._context_menu.add_separator()
        self._context_menu.add_command(label="Delete", command=self._ctx_delete)

        self._ctx_conn_id = None

    def refresh(self, filter_text: str = "", category_filter: int | None = -1):
        for w in self.scroll.winfo_children():
            w.destroy()
        self._widgets.clear()

        categories = db.get_categories()
        all_connections = db.get_connections()

        if filter_text:
            filter_text = filter_text.lower()
            all_connections = [
                c for c in all_connections
                if filter_text in c["name"].lower()
                or filter_text in c["hostname"].lower()
                or filter_text in (c.get("username") or "").lower()
            ]

        if category_filter is not None and category_filter != -1:
            if category_filter == 0:
                all_connections = [c for c in all_connections if c["category_id"] is None]
                categories = []
            else:
                all_connections = [c for c in all_connections if c["category_id"] == category_filter]
                categories = [cat for cat in categories if cat["id"] == category_filter]

        categorized = {}
        uncategorized = []
        for c in all_connections:
            cid = c["category_id"]
            if cid is None:
                uncategorized.append(c)
            else:
                categorized.setdefault(cid, []).append(c)

        for cat in categories:
            cid = cat["id"]
            conns = categorized.get(cid, [])
            if not conns and filter_text:
                continue
            self._render_category(cat, conns)

        if uncategorized:
            self._render_category({"id": None, "name": "Uncategorized"}, uncategorized)

        self._check_status_all(all_connections)

    def _render_category(self, category: dict, connections: list):
        cid = category["id"]
        is_collapsed = self._collapsed.get(cid, False)

        header = ctk.CTkFrame(self.scroll, fg_color="transparent", height=30)
        header.pack(fill="x", pady=(8, 2))
        header.pack_propagate(False)

        arrow = "▶" if is_collapsed else "▼"
        count = len(connections)
        label_text = f" {arrow}  {category['name']}  ({count})"

        label = ctk.CTkLabel(
            header, text=label_text, anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        label.pack(fill="both", expand=True, padx=5)
        label.bind("<Button-1>", lambda e, c=cid: self._toggle_category(c))

        if not is_collapsed:
            for conn in connections:
                self._render_connection(conn)

    def _render_connection(self, conn: dict):
        conn_id = conn["id"]
        is_selected = conn_id == self._selected_id

        frame = ctk.CTkFrame(
            self.scroll, height=36,
            fg_color=("gray75", "gray30") if is_selected else ("gray90", "gray17"),
            corner_radius=6,
        )
        frame.pack(fill="x", padx=(15, 0), pady=1)
        frame.pack_propagate(False)

        status = self._status_cache.get(conn_id, "gray")
        colors = {"green": "#22c55e", "red": "#ef4444", "gray": "#6b7280"}
        dot = ctk.CTkLabel(
            frame, text="●", width=20,
            text_color=colors.get(status, "#6b7280"),
            font=ctk.CTkFont(size=10),
        )
        dot.pack(side="left", padx=(8, 2))

        name_label = ctk.CTkLabel(
            frame, text=conn["name"], anchor="w",
            font=ctk.CTkFont(size=12),
        )
        name_label.pack(side="left", fill="x", expand=True, padx=2)

        host_label = ctk.CTkLabel(
            frame, text=conn["hostname"], anchor="e",
            font=ctk.CTkFont(size=10), text_color="gray",
        )
        host_label.pack(side="right", padx=(2, 8))

        for widget in (frame, dot, name_label, host_label):
            widget.bind("<Button-1>", lambda e, c=conn_id: self._select(c))
            widget.bind("<Double-Button-1>", lambda e, c=conn_id: self._double_click(c))
            widget.bind("<Button-3>", lambda e, c=conn_id: self._show_context(e, c))

        self._widgets[conn_id] = {"frame": frame, "dot": dot}

    def _toggle_category(self, cat_id):
        self._collapsed[cat_id] = not self._collapsed.get(cat_id, False)
        self.refresh()

    def _select(self, conn_id: int):
        self._selected_id = conn_id
        self.refresh()
        if self.on_select:
            self.on_select(conn_id)

    def _double_click(self, conn_id: int):
        if self.on_connect:
            self.on_connect(conn_id)

    def _show_context(self, event, conn_id: int):
        self._ctx_conn_id = conn_id
        self._select(conn_id)
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _ctx_connect(self):
        if self._ctx_conn_id and self.on_connect:
            self.on_connect(self._ctx_conn_id)

    def _ctx_edit(self):
        if self._ctx_conn_id and self.on_edit:
            self.on_edit(self._ctx_conn_id)

    def _ctx_delete(self):
        if self._ctx_conn_id and self.on_delete:
            self.on_delete(self._ctx_conn_id)

    def _ctx_duplicate(self):
        if self._ctx_conn_id and self.on_duplicate:
            self.on_duplicate(self._ctx_conn_id)

    def _check_status_all(self, connections: list):
        for conn in connections:
            t = threading.Thread(
                target=self._check_single, args=(conn["id"], conn["hostname"]),
                daemon=True,
            )
            t.start()

    def _check_single(self, conn_id: int, hostname: str):
        alive = ping_host(hostname)
        self._status_cache[conn_id] = "green" if alive else "red"
        try:
            widget = self._widgets.get(conn_id)
            if widget and widget["dot"].winfo_exists():
                color = "#22c55e" if alive else "#ef4444"
                widget["dot"].configure(text_color=color)
        except Exception:
            pass

    def get_selected_id(self) -> int | None:
        return self._selected_id
