import customtkinter as ctk

from core import database as db


class DetailsPanel(ctk.CTkFrame):
    def __init__(self, parent, on_connect=None, on_edit=None, on_delete=None):
        super().__init__(parent)
        self.on_connect = on_connect
        self.on_edit = on_edit
        self.on_delete = on_delete
        self._conn_id = None

        self._build_empty()

    def _build_empty(self):
        for w in self.winfo_children():
            w.destroy()

        placeholder = ctk.CTkFrame(self, fg_color="transparent")
        placeholder.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(
            placeholder, text="No connection selected",
            font=ctk.CTkFont(size=16), text_color="gray",
        ).pack()
        ctk.CTkLabel(
            placeholder, text="Select a connection from the sidebar\nor add a new one.",
            font=ctk.CTkFont(size=12), text_color="gray",
        ).pack(pady=(5, 0))

    def show_connection(self, conn_id: int):
        conn = db.get_connection_by_id(conn_id)
        if not conn:
            self._build_empty()
            return

        self._conn_id = conn_id

        for w in self.winfo_children():
            w.destroy()

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=15)

        # Header
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            header, text=conn["name"],
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            header, text=f"{conn['hostname']}:{conn.get('port', 3389)}",
            font=ctk.CTkFont(size=14), text_color="gray", anchor="w",
        ).pack(fill="x")

        # Connect button
        connect_btn = ctk.CTkButton(
            scroll, text="Connect", height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#0078d4", hover_color="#106ebe",
            command=lambda: self._do_connect(conn_id),
        )
        connect_btn.pack(fill="x", pady=(0, 20))

        # Info section
        info_frame = ctk.CTkFrame(scroll, fg_color=("gray88", "gray20"), corner_radius=8)
        info_frame.pack(fill="x", pady=(0, 10))

        fields = [
            ("Username", conn.get("username") or "(not set)"),
            ("Port", str(conn.get("port", 3389))),
            ("Password", "********" if conn.get("encrypted_password") else "(not set)"),
        ]

        cat_name = "(None)"
        if conn.get("category_id"):
            cats = db.get_categories()
            cat = next((c for c in cats if c["id"] == conn["category_id"]), None)
            if cat:
                cat_name = cat["name"]
        fields.append(("Category", cat_name))

        if conn.get("last_connected"):
            fields.append(("Last Connected", conn["last_connected"][:19].replace("T", " ")))

        for i, (label, value) in enumerate(fields):
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=6)
            ctk.CTkLabel(row, text=label, width=130, anchor="w",
                         font=ctk.CTkFont(size=12), text_color="gray").pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)

        # RDP Settings section
        ctk.CTkLabel(scroll, text="RDP Settings", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(
            fill="x", pady=(10, 5)
        )

        rdp_frame = ctk.CTkFrame(scroll, fg_color=("gray88", "gray20"), corner_radius=8)
        rdp_frame.pack(fill="x", pady=(0, 10))

        screen_mode = "Fullscreen" if conn.get("screen_mode", 2) == 2 else "Windowed"
        rdp_fields = [
            ("Screen Mode", screen_mode),
            ("Resolution", f"{conn.get('desktop_width', 1920)}x{conn.get('desktop_height', 1080)}"),
            ("Color Depth", f"{conn.get('color_depth', 32)}-bit"),
            ("Clipboard", "Yes" if conn.get("redirect_clipboard") else "No"),
            ("Printers", "Yes" if conn.get("redirect_printers") else "No"),
            ("Drives", "Yes" if conn.get("redirect_drives") else "No"),
        ]

        for label, value in rdp_fields:
            row = ctk.CTkFrame(rdp_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=4)
            ctk.CTkLabel(row, text=label, width=130, anchor="w",
                         font=ctk.CTkFont(size=12), text_color="gray").pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w",
                         font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)

        # Notes
        notes = conn.get("notes", "").strip()
        if notes:
            ctk.CTkLabel(scroll, text="Notes", font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(
                fill="x", pady=(10, 5)
            )
            notes_frame = ctk.CTkFrame(scroll, fg_color=("gray88", "gray20"), corner_radius=8)
            notes_frame.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(notes_frame, text=notes, anchor="nw", justify="left",
                         wraplength=400).pack(fill="x", padx=15, pady=10)

        # Action buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            btn_frame, text="Edit", width=100, fg_color=("gray70", "gray35"),
            hover_color=("gray60", "gray45"),
            command=lambda: self._do_edit(conn_id),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Delete", width=100,
            fg_color="#dc2626", hover_color="#b91c1c",
            command=lambda: self._do_delete(conn_id),
        ).pack(side="left")

    def _do_connect(self, conn_id: int):
        if self.on_connect:
            self.on_connect(conn_id)

    def _do_edit(self, conn_id: int):
        if self.on_edit:
            self.on_edit(conn_id)

    def _do_delete(self, conn_id: int):
        if self.on_delete:
            self.on_delete(conn_id)

    def clear(self):
        self._conn_id = None
        self._build_empty()
