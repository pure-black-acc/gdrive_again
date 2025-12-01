# app.py — Modern Google Drive Manager
import os
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO

# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

SCOPES = ['https://www.googleapis.com/auth/drive']

class ModernDriveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Drive Manager")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        self.service = None
        self.files = []
        self.selected_file_id = None
        self.current_folder_id = None
        self.breadcrumb_stack = []
        self.loading = False

        # Color scheme - Monochrome Black & White
        self.colors = {
            "primary": "#ffffff",
            "primary_hover": "#e5e5e5",
            "secondary": "#808080",
            "success": "#ffffff",
            "danger": "#ffffff",
            "bg_dark": "#000000",
            "bg_card": "#1a1a1a",
            "bg_hover": "#2d2d2d",
            "text_primary": "#ffffff",
            "text_secondary": "#a0a0a0"
        }
        
        # Font family
        self.font_family = "JetBrainsMono Nerd Font"
        self.ui_font = "Segoe UI"  # Clean UI font for labels

        self.create_widgets()
        self.auto_login()

    def create_widgets(self):
        # === SIDEBAR ===
        self.sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0, fg_color=self.colors["bg_dark"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo/Title
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.pack(pady=30, padx=20)
        
        ctk.CTkLabel(
            title_frame,
            text="📁",
            font=ctk.CTkFont(size=48)
        ).pack()
        
        ctk.CTkLabel(
            title_frame,
            text="Drive Manager",
            font=ctk.CTkFont(family=self.font_family, size=20, weight="bold"),
            text_color=self.colors["text_primary"]
        ).pack()

        # Login Section
        self.login_frame = ctk.CTkFrame(self.sidebar, fg_color=self.colors["bg_card"], corner_radius=10)
        self.login_frame.pack(pady=20, padx=20, fill="x")

        self.login_button = ctk.CTkButton(
            self.login_frame,
            text="🔐 Sign in with Google",
            command=self.manual_login,
            fg_color=self.colors["primary"],
            hover_color=self.colors["primary_hover"],
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(family=self.font_family, size=14, weight="bold")
        )
        self.login_button.pack(pady=15, padx=15)

        # Quick Actions
        self.actions_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.actions_frame.pack(pady=20, padx=20, fill="x")

        ctk.CTkLabel(
            self.actions_frame,
            text="Quick Actions",
            font=ctk.CTkFont(family=self.font_family, size=12, weight="bold"),
            text_color=self.colors["text_secondary"]
        ).pack(anchor="w", pady=(0, 10))

        self.download_btn_sidebar = ctk.CTkButton(
            self.actions_frame,
            text="⬇️ Download",
            command=self.download_file,
            state="disabled",
            fg_color=self.colors["success"],
            hover_color="#059669",
            height=35,
            corner_radius=8
        )
        self.download_btn_sidebar.pack(fill="x", pady=5)

        self.rename_btn_sidebar = ctk.CTkButton(
            self.actions_frame,
            text="✏️ Rename",
            command=self.rename_file,
            state="disabled",
            fg_color=self.colors["bg_hover"],
            hover_color=self.colors["secondary"],
            height=35,
            corner_radius=8
        )
        self.rename_btn_sidebar.pack(fill="x", pady=5)

        self.move_btn_sidebar = ctk.CTkButton(
            self.actions_frame,
            text="📁 Move",
            command=self.move_file,
            state="disabled",
            fg_color=self.colors["bg_hover"],
            hover_color=self.colors["secondary"],
            height=35,
            corner_radius=8
        )
        self.move_btn_sidebar.pack(fill="x", pady=5)

        # Status at bottom
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.pack(side="bottom", pady=20, padx=20, fill="x")

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="● Not signed in",
            font=ctk.CTkFont(family=self.ui_font, size=12),
            text_color=self.colors["text_secondary"]
        )
        self.status_label.pack()

        # Download progress (hidden by default)
        self.progress_frame = ctk.CTkFrame(self.sidebar, fg_color=self.colors["bg_card"], corner_radius=10)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="Downloading...",
            font=ctk.CTkFont(family=self.ui_font, size=12),
            text_color=self.colors["text_primary"]
        )
        self.progress_label.pack(pady=(10, 5), padx=10)
        
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            width=200,
            height=8,
            corner_radius=4,
            fg_color=self.colors["bg_hover"],
            progress_color=self.colors["primary"]
        )
        self.progress_bar.pack(pady=(0, 10), padx=10)
        self.progress_bar.set(0)
        
        self.progress_text = ctk.CTkLabel(
            self.progress_frame,
            text="0%",
            font=ctk.CTkFont(family=self.ui_font, size=11),
            text_color=self.colors["text_secondary"]
        )
        self.progress_text.pack(pady=(0, 10), padx=10)

        # === MAIN CONTENT ===
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="#0a0f1e")
        self.main_frame.pack(side="right", fill="both", expand=True)

        # Header with breadcrumb
        self.header = ctk.CTkFrame(self.main_frame, height=80, corner_radius=0, fg_color=self.colors["bg_card"])
        self.header.pack(fill="x", padx=0, pady=0)
        self.header.pack_propagate(False)

        # Breadcrumb
        self.breadcrumb_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.breadcrumb_frame.pack(side="left", padx=30, pady=20)

        # Search bar (placeholder)
        search_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        search_frame.pack(side="right", padx=30, pady=20)

        # Content area with scrollable grid
        self.content_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Loading indicator
        self.loading_label = ctk.CTkLabel(
            self.content_container,
            text="",
            font=ctk.CTkFont(family=self.font_family, size=16),
            text_color=self.colors["text_secondary"]
        )
        self.loading_label.pack(expand=True)

        # Scrollable grid
        self.grid_frame = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
            scrollbar_button_color=self.colors["bg_hover"],
            scrollbar_button_hover_color=self.colors["secondary"]
        )

    def auto_login(self):
        if os.path.exists("token.json"):
            def _auto():
                try:
                    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
                    if creds.valid:
                        self.service = build("drive", "v3", credentials=creds)
                        self.root.after(0, self.on_login_success)
                    elif creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        with open("token.json", "w") as token:
                            token.write(creds.to_json())
                        self.service = build("drive", "v3", credentials=creds)
                        self.root.after(0, self.on_login_success)
                except Exception as e:
                    print(f"Auto-login failed: {e}")
            
            threading.Thread(target=_auto, daemon=True).start()

    def manual_login(self):
        def _login():
            try:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
                with open("token.json", "w") as token:
                    token.write(creds.to_json())
                self.service = build("drive", "v3", credentials=creds)
                self.root.after(0, self.on_login_success)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Login Failed", str(e)))

        threading.Thread(target=_login, daemon=True).start()

    def on_login_success(self):
        self.login_button.configure(text="✅ Signed in", state="disabled", fg_color=self.colors["success"])
        self.status_label.configure(text="● Connected", text_color=self.colors["success"])
        self.go_to_folder(None)

    def go_to_folder(self, folder_id):
        if self.loading:
            return
        
        self.loading = True
        self.show_loading()

        def _load():
            try:
                query = "trashed=false and 'root' in parents" if folder_id is None else f"trashed=false and '{folder_id}' in parents"
                
                result = self.service.files().list(
                    q=query,
                    pageSize=100,
                    fields="files(id, name, mimeType, iconLink, modifiedTime)",
                    orderBy="folder,name"
                ).execute()
                
                self.files = result.get("files", [])
                self.current_folder_id = folder_id
                
                self.root.after(0, self.update_breadcrumb)
                self.root.after(0, self.populate_grid)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load folder:\n{e}"))
            finally:
                self.loading = False

        threading.Thread(target=_load, daemon=True).start()

    def show_loading(self):
        self.loading_label.configure(text="⏳ Loading...")
        self.loading_label.pack(expand=True)
        self.grid_frame.pack_forget()

    def hide_loading(self):
        self.loading_label.pack_forget()
        self.grid_frame.pack(fill="both", expand=True)

    def update_breadcrumb(self):
        for widget in self.breadcrumb_frame.winfo_children():
            widget.destroy()

        home_btn = ctk.CTkButton(
            self.breadcrumb_frame,
            text="🏠 Home",
            command=lambda: self.navigate_to_breadcrumb(None),
            width=80,
            height=32,
            fg_color="transparent",
            hover_color=self.colors["bg_hover"],
            text_color=self.colors["text_primary"],
            font=ctk.CTkFont(family=self.font_family, size=13)
        )
        home_btn.pack(side="left", padx=2)

        for idx, (folder_id, folder_name) in enumerate(self.breadcrumb_stack):
            ctk.CTkLabel(
                self.breadcrumb_frame,
                text="›",
                text_color=self.colors["text_secondary"],
                font=ctk.CTkFont(family=self.font_family, size=16)
            ).pack(side="left", padx=5)

            btn = ctk.CTkButton(
                self.breadcrumb_frame,
                text=folder_name[:20] + "..." if len(folder_name) > 20 else folder_name,
                command=lambda fid=folder_id, i=idx: self.navigate_to_breadcrumb(fid, i),
                width=100,
                height=32,
                fg_color="transparent",
                hover_color=self.colors["bg_hover"],
                text_color=self.colors["text_primary"],
                font=ctk.CTkFont(family=self.font_family, size=13)
            )
            btn.pack(side="left", padx=2)

    def populate_grid(self):
        self.hide_loading()
        
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        if not self.files:
            empty_label = ctk.CTkLabel(
                self.grid_frame,
                text="📂 This folder is empty",
                font=ctk.CTkFont(family=self.ui_font, size=18),
                text_color=self.colors["text_secondary"]
            )
            empty_label.pack(expand=True, pady=50)
            return

        # Create responsive grid
        columns = 4
        for i, f in enumerate(self.files):
            row = i // columns
            col = i % columns

            is_folder = f["mimeType"] == "application/vnd.google-apps.folder"
            
            # Card
            card = ctk.CTkFrame(
                self.grid_frame,
                width=220,
                height=180,
                corner_radius=12,
                fg_color=self.colors["bg_card"],
                border_width=2,
                border_color=self.colors["bg_card"]
            )
            card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
            card.grid_propagate(False)

            # Icon
            icon_text = "📁" if is_folder else "📄"
            icon_label = ctk.CTkLabel(
                card,
                text=icon_text,
                font=ctk.CTkFont(size=56)
            )
            icon_label.pack(pady=(20, 10))

            # Name
            name_display = f["name"][:30] + "..." if len(f["name"]) > 30 else f["name"]
            name_label = ctk.CTkLabel(
                card,
                text=name_display,
                font=ctk.CTkFont(family=self.ui_font, size=13, weight="bold"),
                text_color=self.colors["text_primary"],
                wraplength=200
            )
            name_label.pack(pady=(0, 5))

            # Type
            type_label = ctk.CTkLabel(
                card,
                text="Folder" if is_folder else "File",
                font=ctk.CTkFont(family=self.ui_font, size=11),
                text_color=self.colors["text_secondary"]
            )
            type_label.pack()

            # Bind events
            card.file_id = f["id"]
            card.file_name = f["name"]
            card.is_folder = is_folder

            if is_folder:
                card.bind("<Button-1>", lambda e, fid=f["id"], fname=f["name"]: self.on_folder_click(fid, fname))
                for child in card.winfo_children():
                    child.bind("<Button-1>", lambda e, fid=f["id"], fname=f["name"]: self.on_folder_click(fid, fname))
            else:
                card.bind("<Button-1>", lambda e, fid=f["id"], fname=f["name"]: self.on_file_click(fid, fname, e.widget))
                for child in card.winfo_children():
                    child.bind("<Button-1>", lambda e, fid=f["id"], fname=f["name"], c=card: self.on_file_click(fid, fname, c))

            card.bind("<Enter>", lambda e, w=card: w.configure(border_color=self.colors["primary"]))
            card.bind("<Leave>", lambda e, w=card: w.configure(border_color=self.colors["bg_card"]) if not hasattr(w, 'selected') else None)

        for i in range(columns):
            self.grid_frame.grid_columnconfigure(i, weight=1)

    def navigate_to_breadcrumb(self, folder_id, index=None):
        """Navigate to a folder from breadcrumb, resetting the path"""
        if folder_id is None:
            # Going to root, clear all breadcrumbs
            self.breadcrumb_stack = []
        elif index is not None:
            # Going to a specific breadcrumb, keep only items up to that index
            self.breadcrumb_stack = self.breadcrumb_stack[:index + 1]
        
        self.go_to_folder(folder_id)

    def show_context_menu_at_button_delayed(self, file_id, file_name, is_folder):
        """Show context menu - delayed to get proper widget position"""
        # Store selected item info
        self.selected_file_id = file_id
        self.selected_file_name = file_name
        
        # Find the button widget by searching through grid
        button_widget = None
        for widget in self.grid_frame.winfo_children():
            if hasattr(widget, 'file_id') and widget.file_id == file_id:
                if hasattr(widget, 'menu_btn'):
                    button_widget = widget.menu_btn
                    break
        
        if button_widget:
            # Get button position
            x = button_widget.winfo_rootx()
            y = button_widget.winfo_rooty() + button_widget.winfo_height()
            
            print(f"Menu button clicked for: {file_name} at {x}, {y}")  # Debug
            
            # Create context menu using tkinter Menu
            import tkinter as tk
            
            menu = tk.Menu(self.root, tearoff=0, 
                          bg="#1a1a1a", 
                          fg="#ffffff", 
                          activebackground="#2d2d2d", 
                          activeforeground="#ffffff",
                          borderwidth=2, 
                          relief="solid",
                          font=(self.ui_font, 11))
            
            if is_folder:
                # Folder options
                menu.add_command(label="📂 Open", 
                               command=lambda: self.on_folder_click(file_id, file_name))
            else:
                # File options
                menu.add_command(label="⬇️ Download", 
                               command=self.download_file)
            
            # Common options
            menu.add_separator()
            menu.add_command(label="✏️ Rename", 
                            command=self.rename_file)
            menu.add_command(label="📁 Move", 
                            command=self.move_file)
            
            menu.add_separator()
            menu.add_command(label="🗑️ Delete", 
                            command=lambda: self.delete_file(file_id, file_name),
                            foreground="#ef4444")
            
            try:
                menu.tk_popup(x, y)
            finally:
                menu.grab_release()

    def show_context_menu_at_button(self, button_widget, file_id, file_name, is_folder):
        """Show context menu below the button"""
        print(f"Menu button clicked for: {file_name}")  # Debug
        
        # Store selected item info
        self.selected_file_id = file_id
        self.selected_file_name = file_name
        
        # Get button position
        x = button_widget.winfo_rootx()
        y = button_widget.winfo_rooty() + button_widget.winfo_height()
        
        # Create context menu using tkinter Menu
        import tkinter as tk
        
        menu = tk.Menu(self.root, tearoff=0, 
                      bg="#1a1a1a", 
                      fg="#ffffff", 
                      activebackground="#2d2d2d", 
                      activeforeground="#ffffff",
                      borderwidth=2, 
                      relief="solid",
                      font=(self.ui_font, 11))
        
        if is_folder:
            # Folder options
            menu.add_command(label="📂 Open", 
                           command=lambda: self.on_folder_click(file_id, file_name))
        else:
            # File options
            menu.add_command(label="⬇️ Download", 
                           command=self.download_file)
        
        # Common options
        menu.add_separator()
        menu.add_command(label="✏️ Rename", 
                        command=self.rename_file)
        menu.add_command(label="📁 Move", 
                        command=self.move_file)
        
        menu.add_separator()
        menu.add_command(label="🗑️ Delete", 
                        command=lambda: self.delete_file(file_id, file_name),
                        foreground="#ef4444")
        
        try:
            print(f"Showing menu at: {x}, {y}")  # Debug
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def show_context_menu(self, event, file_id, file_name, is_folder):
        """Show context menu on right click (kept for compatibility but may not work on Windows)"""
        print(f"Context menu triggered for: {file_name}, is_folder: {is_folder}")  # Debug
        
        # Store selected item info
        self.selected_file_id = file_id
        self.selected_file_name = file_name
        
        # Create context menu using tkinter Menu for better compatibility
        import tkinter as tk
        
        menu = tk.Menu(self.root, tearoff=0, 
                      bg="#1a1a1a", 
                      fg="#ffffff", 
                      activebackground="#2d2d2d", 
                      activeforeground="#ffffff",
                      borderwidth=2, 
                      relief="solid",
                      font=(self.ui_font, 11))
        
        if is_folder:
            # Folder options
            menu.add_command(label="📂 Open", 
                           command=lambda: self.on_folder_click(file_id, file_name))
        else:
            # File options
            menu.add_command(label="⬇️ Download", 
                           command=self.download_file)
        
        # Common options
        menu.add_separator()
        menu.add_command(label="✏️ Rename", 
                        command=self.rename_file)
        menu.add_command(label="📁 Move", 
                        command=self.move_file)
        
        menu.add_separator()
        menu.add_command(label="🗑️ Delete", 
                        command=lambda: self.delete_file(file_id, file_name),
                        foreground="#ef4444")
        
        try:
            print(f"Showing menu at: {event.x_root}, {event.y_root}")  # Debug
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        
        return "break"  # Prevent event propagation

    def on_folder_click(self, folder_id, folder_name):
        """Navigate into a folder"""
        # Add folder to breadcrumb stack
        self.breadcrumb_stack.append((folder_id, folder_name))
        self.go_to_folder(folder_id)

    def on_file_click(self, file_id, file_name, card):
        self.selected_file_id = file_id
        self.selected_file_name = file_name
        self.download_btn_sidebar.configure(state="normal")
        self.rename_btn_sidebar.configure(state="normal")
        self.move_btn_sidebar.configure(state="normal")

        # Highlight
        for widget in self.grid_frame.winfo_children():
            if hasattr(widget, 'file_id'):
                if widget.file_id == file_id:
                    widget.configure(border_color=self.colors["primary"], fg_color=self.colors["bg_hover"])
                    widget.selected = True
                else:
                    widget.configure(border_color=self.colors["bg_card"], fg_color=self.colors["bg_card"])
                    widget.selected = False

    def get_current_folder_name(self):
        if self.breadcrumb_stack:
            return self.breadcrumb_stack[-1][1]
        return "Root"

    def download_file(self):
        if not self.selected_file_id:
            return

        save_path = filedialog.asksaveasfilename(initialfile=self.selected_file_name)
        if not save_path:
            return

        # Show progress bar
        self.progress_frame.pack(side="bottom", pady=(0, 20), padx=20, fill="x", before=self.status_frame)
        self.progress_bar.set(0)
        self.progress_text.configure(text="0%")
        self.progress_label.configure(text=f"Downloading {self.selected_file_name[:20]}...")
        
        def _download():
            try:
                # Get file metadata for size
                file_metadata = self.service.files().get(
                    fileId=self.selected_file_id, 
                    fields='size'
                ).execute()
                
                file_size = int(file_metadata.get('size', 0))
                
                request = self.service.files().get_media(fileId=self.selected_file_id)
                fh = BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = status.progress()
                        self.root.after(0, lambda p=progress: self.update_progress(p))
                
                # Save file
                with open(save_path, "wb") as f:
                    fh.seek(0)
                    f.write(fh.read())
                
                # Complete
                self.root.after(0, lambda: self.update_progress(1.0))
                self.root.after(500, lambda: self.hide_progress())
                self.root.after(500, lambda: messagebox.showinfo("Success", f"✅ Downloaded:\n{save_path}"))
                
            except Exception as e:
                self.root.after(0, lambda: self.hide_progress())
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=_download, daemon=True).start()

    def update_progress(self, value):
        """Update progress bar value"""
        self.progress_bar.set(value)
        percentage = int(value * 100)
        self.progress_text.configure(text=f"{percentage}%")
    
    def hide_progress(self):
        """Hide progress bar"""
        self.progress_frame.pack_forget()

    def rename_file(self):
        """Rename the selected file"""
        if not self.selected_file_id:
            return

        # Create rename dialog
        dialog = ctk.CTkInputDialog(
            text=f"Enter new name for:\n{self.selected_file_name}",
            title="Rename File"
        )
        new_name = dialog.get_input()

        if not new_name or new_name == self.selected_file_name:
            return

        def _rename():
            try:
                self.service.files().update(
                    fileId=self.selected_file_id,
                    body={'name': new_name}
                ).execute()

                self.root.after(0, lambda: messagebox.showinfo("Success", f"✅ Renamed to:\n{new_name}"))
                self.root.after(0, lambda: self.go_to_folder(self.current_folder_id))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to rename:\n{e}"))

        threading.Thread(target=_rename, daemon=True).start()

    def move_file(self):
        """Move the selected file to another folder"""
        if not self.selected_file_id:
            return

        # Create folder selection dialog
        self.show_folder_selector()

    def show_folder_selector(self):
        """Show a dialog to select destination folder with hierarchical tree view"""
        # Create new window
        selector_window = ctk.CTkToplevel(self.root)
        selector_window.title("Move to Folder")
        selector_window.geometry("600x700")
        selector_window.grab_set()

        # Title with current file info
        title_label = ctk.CTkLabel(
            selector_window,
            text=f"Move: {self.selected_file_name[:40]}...",
            font=ctk.CTkFont(family=self.font_family, size=16, weight="bold")
        )
        title_label.pack(pady=20)

        # Current location indicator
        current_location = ctk.CTkLabel(
            selector_window,
            text="Select destination folder:",
            font=ctk.CTkFont(family=self.ui_font, size=12),
            text_color=self.colors["text_secondary"]
        )
        current_location.pack(pady=(0, 10))

        # Navigation frame (breadcrumb for folder selector)
        nav_frame = ctk.CTkFrame(selector_window, fg_color=self.colors["bg_card"], height=50)
        nav_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Folder tree frame
        tree_frame = ctk.CTkScrollableFrame(
            selector_window,
            fg_color="transparent"
        )
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Store current navigation state
        nav_state = {"current_folder": None, "breadcrumb": []}

        def update_nav_breadcrumb():
            """Update navigation breadcrumb in selector"""
            for widget in nav_frame.winfo_children():
                widget.destroy()

            home_btn = ctk.CTkButton(
                nav_frame,
                text="🏠 My Drive",
                command=lambda: load_folder_contents(None),
                fg_color="transparent",
                hover_color=self.colors["bg_hover"],
                font=ctk.CTkFont(family=self.ui_font, size=12),
                height=30
            )
            home_btn.pack(side="left", padx=5, pady=10)

            for folder_id, folder_name in nav_state["breadcrumb"]:
                ctk.CTkLabel(
                    nav_frame,
                    text="›",
                    text_color=self.colors["text_secondary"],
                    font=ctk.CTkFont(size=14)
                ).pack(side="left", padx=3)

                btn = ctk.CTkButton(
                    nav_frame,
                    text=folder_name[:15] + "..." if len(folder_name) > 15 else folder_name,
                    command=lambda fid=folder_id: load_folder_contents(fid),
                    fg_color="transparent",
                    hover_color=self.colors["bg_hover"],
                    font=ctk.CTkFont(family=self.ui_font, size=12),
                    height=30
                )
                btn.pack(side="left", padx=3)

        def load_folder_contents(folder_id):
            """Load folders in the current directory"""
            # Clear tree
            for widget in tree_frame.winfo_children():
                widget.destroy()

            loading = ctk.CTkLabel(
                tree_frame,
                text="Loading folders...",
                font=ctk.CTkFont(family=self.ui_font, size=13),
                text_color=self.colors["text_secondary"]
            )
            loading.pack(pady=20)

            def _load():
                try:
                    # Build query
                    if folder_id is None:
                        query = "mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false"
                    else:
                        query = f"mimeType='application/vnd.google-apps.folder' and '{folder_id}' in parents and trashed=false"

                    result = self.service.files().list(
                        q=query,
                        pageSize=100,
                        fields="files(id, name)",
                        orderBy="name"
                    ).execute()

                    folders = result.get("files", [])
                    nav_state["current_folder"] = folder_id

                    def update_ui():
                        loading.destroy()
                        update_nav_breadcrumb()

                        # "Move here" button for current folder
                        move_here_frame = ctk.CTkFrame(tree_frame, fg_color=self.colors["bg_card"])
                        move_here_frame.pack(fill="x", pady=(0, 15))

                        move_here_btn = ctk.CTkButton(
                            move_here_frame,
                            text="📍 Move Here",
                            command=lambda: self.execute_move(folder_id, selector_window),
                            fg_color=self.colors["primary"],
                            hover_color=self.colors["primary_hover"],
                            height=45,
                            font=ctk.CTkFont(family=self.font_family, size=14, weight="bold")
                        )
                        move_here_btn.pack(fill="x", padx=10, pady=10)

                        # Show subfolders
                        if folders:
                            ctk.CTkLabel(
                                tree_frame,
                                text="Folders:",
                                font=ctk.CTkFont(family=self.ui_font, size=12, weight="bold"),
                                text_color=self.colors["text_secondary"]
                            ).pack(anchor="w", pady=(10, 5))

                            for folder in folders:
                                folder_frame = ctk.CTkFrame(tree_frame, fg_color=self.colors["bg_card"])
                                folder_frame.pack(fill="x", pady=3)

                                # Open folder button (navigate into it)
                                open_btn = ctk.CTkButton(
                                    folder_frame,
                                    text=f"📁 {folder['name']}",
                                    command=lambda fid=folder['id'], fname=folder['name']: navigate_into_folder(fid, fname),
                                    fg_color="transparent",
                                    hover_color=self.colors["bg_hover"],
                                    anchor="w",
                                    height=40,
                                    font=ctk.CTkFont(family=self.ui_font, size=13)
                                )
                                open_btn.pack(side="left", fill="x", expand=True, padx=5, pady=5)

                                # Arrow indicator
                                ctk.CTkLabel(
                                    folder_frame,
                                    text="›",
                                    text_color=self.colors["text_secondary"],
                                    font=ctk.CTkFont(size=18)
                                ).pack(side="right", padx=10)

                        else:
                            ctk.CTkLabel(
                                tree_frame,
                                text="No subfolders",
                                font=ctk.CTkFont(family=self.ui_font, size=12),
                                text_color=self.colors["text_secondary"]
                            ).pack(pady=20)

                    selector_window.after(0, update_ui)

                except Exception as e:
                    selector_window.after(0, lambda: loading.configure(text=f"Error: {e}"))

            threading.Thread(target=_load, daemon=True).start()

        def navigate_into_folder(folder_id, folder_name):
            """Navigate into a subfolder"""
            nav_state["breadcrumb"].append((folder_id, folder_name))
            load_folder_contents(folder_id)

        # Initial load (root)
        load_folder_contents(None)

        # Cancel button
        cancel_btn = ctk.CTkButton(
            selector_window,
            text="Cancel",
            command=selector_window.destroy,
            fg_color=self.colors["bg_hover"],
            hover_color=self.colors["secondary"],
            height=40,
            font=ctk.CTkFont(family=self.font_family, size=13)
        )
        cancel_btn.pack(pady=(0, 20), padx=20, fill="x")

    def execute_move(self, destination_folder_id, dialog_window):
        """Execute the move operation"""
        dialog_window.destroy()

        def _move():
            try:
                # Get current parents
                file = self.service.files().get(
                    fileId=self.selected_file_id,
                    fields='parents'
                ).execute()

                previous_parents = ",".join(file.get('parents', []))

                # Move file
                self.service.files().update(
                    fileId=self.selected_file_id,
                    addParents=destination_folder_id if destination_folder_id else 'root',
                    removeParents=previous_parents,
                    fields='id, parents'
                ).execute()

                dest_name = "My Drive (Root)" if not destination_folder_id else "selected folder"
                self.root.after(0, lambda: messagebox.showinfo("Success", f"✅ Moved to {dest_name}"))
                self.root.after(0, lambda: self.go_to_folder(self.current_folder_id))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to move file:\n{e}"))

        threading.Thread(target=_move, daemon=True).start()

    def delete_file(self, file_id, file_name):
        """Delete (trash) a file or folder"""
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Move to trash:\n{file_name}\n\nAre you sure?"
        )
        
        if not confirm:
            return
        
        def _delete():
            try:
                self.service.files().update(
                    fileId=file_id,
                    body={'trashed': True}
                ).execute()
                
                self.root.after(0, lambda: messagebox.showinfo("Success", f"✅ Moved to trash:\n{file_name}"))
                self.root.after(0, lambda: self.go_to_folder(self.current_folder_id))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to delete:\n{e}"))
        
        threading.Thread(target=_delete, daemon=True).start()

if __name__ == "__main__":
    root = ctk.CTk()
    app = ModernDriveApp(root)
    root.mainloop()