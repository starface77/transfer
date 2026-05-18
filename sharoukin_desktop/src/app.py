"""Sharoukin Desktop App GUI."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from agent import SharoukinAgent


class SharoukinDesktopApp:
    """Beautiful, high-fidelity premium desktop GUI for the Sharoukin Agent."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("🛋️  SHAROUKIN DESKTOP AGENT")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)

        # High-end DeepTech dark/neon color palette
        self.colors = {
            "bg_main": "#121214",       # Deep Obsidian
            "bg_card": "#1A1A1E",       # Charcoal
            "bg_input": "#252529",      # Soft Grey
            "fg_main": "#E1E1E6",       # High contrast white/grey
            "accent_neon": "#FF4081",   # Cyber Pink
            "neon_green": "#00E676",    # Cyber Green
            "neon_cyan": "#00E5FF",     # Cyber Cyan
            "neon_purple": "#D500F9",   # Cyber Purple
            "neon_yellow": "#FFD600",   # Cyber Yellow
        }

        # Apply dark mode styles to the main window
        self.root.configure(bg=self.colors["bg_main"])

        # Configure Tkinter style overrides
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            ".",
            background=self.colors["bg_main"],
            foreground=self.colors["fg_main"],
            fieldbackground=self.colors["bg_input"],
        )

        self.setup_ui()

    def setup_ui(self) -> None:
        """Construct the premium layout grid."""
        # --- Top Header Panel ---
        header_frame = tk.Frame(self.root, bg=self.colors["bg_card"], height=60)
        header_frame.pack(fill="x", padx=10, pady=10)

        header_label = tk.Label(
            header_frame,
            text="🛋️  SHAROUKIN AGENT SYSTEM",
            font=("Consolas", 16, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["accent_neon"],
        )
        header_label.pack(side="left", padx=15, pady=10)

        self.status_indicator = tk.Label(
            header_frame,
            text="💤 IDLE",
            font=("Consolas", 10, "bold"),
            bg=self.colors["bg_input"],
            fg=self.colors["neon_cyan"],
            padx=10,
            pady=4,
        )
        self.status_indicator.pack(side="right", padx=15, pady=10)

        # --- Middle Workspace & Task Input ---
        input_frame = tk.Frame(self.root, bg=self.colors["bg_main"])
        input_frame.pack(fill="x", padx=10, pady=5)

        # Workspace path
        path_label = tk.Label(
            input_frame,
            text="📁 WORKSPACE PATH:",
            font=("Consolas", 10, "bold"),
            bg=self.colors["bg_main"],
            fg=self.colors["fg_main"],
        )
        path_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.path_entry = tk.Entry(
            input_frame,
            font=("Consolas", 10),
            bg=self.colors["bg_card"],
            fg=self.colors["fg_main"],
            insertbackground=self.colors["fg_main"],
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["bg_input"],
            highlightcolor=self.colors["neon_cyan"],
        )
        self.path_entry.insert(0, r"c:\Users\danik\Documents\Field")
        self.path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Task description prompt
        prompt_label = tk.Label(
            input_frame,
            text="🧠 CHOOSE TASK OBJECTIVE:",
            font=("Consolas", 10, "bold"),
            bg=self.colors["bg_main"],
            fg=self.colors["fg_main"],
        )
        prompt_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)

        self.prompt_entry = tk.Entry(
            input_frame,
            font=("Consolas", 11),
            bg=self.colors["bg_card"],
            fg=self.colors["fg_main"],
            insertbackground=self.colors["fg_main"],
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["bg_input"],
            highlightcolor=self.colors["accent_neon"],
        )
        self.prompt_entry.insert(0, "Исправь баг с путями на Windows в storage.py")
        self.prompt_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        input_frame.columnconfigure(1, weight=1)

        # --- Launch Button ---
        self.launch_btn = tk.Button(
            self.root,
            text="🚀 ЗАПУСТИТЬ ШАРОУКИНА",
            font=("Consolas", 11, "bold"),
            bg=self.colors["accent_neon"],
            fg="#FFFFFF",
            activebackground=self.colors["neon_purple"],
            activeforeground="#FFFFFF",
            bd=0,
            pady=8,
            cursor="hand2",
            command=self.start_agent,
        )
        self.launch_btn.pack(fill="x", padx=15, pady=10)

        # --- Bottom Console Output (Terminal Panel) ---
        console_frame = tk.Frame(self.root, bg=self.colors["bg_card"])
        console_frame.pack(fill="both", expand=True, padx=10, pady=10)

        console_header = tk.Label(
            console_frame,
            text="🖥️ SHAROUKIN COGNITIVE LOGS",
            font=("Consolas", 9, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["neon_cyan"],
        )
        console_header.pack(anchor="w", padx=10, pady=5)

        self.log_area = ScrolledText(
            console_frame,
            font=("Consolas", 10),
            bg=self.colors["bg_main"],
            fg=self.colors["fg_main"],
            bd=0,
            insertbackground=self.colors["fg_main"],
            highlightthickness=1,
            highlightbackground=self.colors["bg_input"],
        )
        self.log_area.pack(fill="both", expand=True, padx=5, pady=5)

        # Define text styles tags in terminal ScrolledText
        self.log_area.tag_config("info", foreground=self.colors["neon_cyan"])
        self.log_area.tag_config("success", foreground=self.colors["neon_green"])
        self.log_area.tag_config("warning", foreground=self.colors["neon_yellow"])
        self.log_area.tag_config("error", foreground=self.colors["accent_neon"], font=("Consolas", 10, "bold"))
        self.log_area.tag_config("system", foreground=self.colors["neon_purple"], font=("Consolas", 10, "bold"))
        self.log_area.tag_config("default", foreground=self.colors["fg_main"])

    def pipe_log(self, text: str, tag: str = "default") -> None:
        """Thread-safe logging pipe into the styled console panel."""
        self.log_area.insert("end", text + "\n", tag)
        self.log_area.see("end")

    def start_agent(self) -> None:
        """Trigger agent thread to prevent GUI freezing."""
        workspace = self.path_entry.get().strip()
        task = self.prompt_entry.get().strip()

        if not workspace or not task:
            messagebox.showwarning("⚠️ Warning", "Please fill out both Workspace and Task fields.")
            return

        self.launch_btn.config(state="disabled", bg=self.colors["bg_input"])
        self.status_indicator.config(text="🧠 THINKING", fg=self.colors["accent_neon"])
        self.log_area.delete("1.0", "end")

        # Run cognitive agent thread
        agent_thread = threading.Thread(
            target=self.run_agent_cycle,
            args=(workspace, task),
            daemon=True,
        )
        agent_thread.start()

    def run_agent_cycle(self, workspace: str, task: str) -> None:
        """Run the actual reasoning loops of the agent."""
        agent = SharoukinAgent(workspace, self.pipe_log)
        success = agent.execute_task(task)

        # Restore GUI state on completion
        self.root.after(0, self.agent_completed, success)

    def agent_completed(self, success: bool) -> None:
        self.launch_btn.config(state="normal", bg=self.colors["accent_neon"])
        if success:
            self.status_indicator.config(text="✔ SOLVED", fg=self.colors["neon_green"])
        else:
            self.status_indicator.config(text="❌ FAILED", fg=self.colors["accent_neon"])


def main() -> None:
    # Set Windows console environment UTF-8 reconfigure
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    root = tk.Tk()
    app = SharoukinDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
