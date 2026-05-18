"""Sharoukin Desktop App GUI (Google Jules Clone)."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from agent import SharoukinAgent


class SharoukinDesktopApp:
    """Stunning, premium, Google Jules-inspired multi-panel Desktop Dashboard for Sharrowkyn."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("🦅  SHARROWKYN DESTRUCTIVE ENGINE (CO-PILOT)")
        self.root.geometry("1100x750")
        self.root.minsize(950, 600)

        # High-end Obsidian / Cyber-neon color palette
        self.colors = {
            "bg_main": "#121214",       # Obsidian Dark
            "bg_card": "#1A1A1E",       # Charcoal Slate
            "bg_input": "#252529",      # Slate Grey
            "fg_main": "#E1E1E6",       # High contrast grey
            "accent_pink": "#FF4081",   # Cyber Pink
            "neon_green": "#00E676",    # Cyber Green
            "neon_cyan": "#00E5FF",     # Cyber Cyan
            "neon_purple": "#D500F9",   # Cyber Purple
            "neon_yellow": "#FFD600",   # Cyber Yellow
            "diff_add": "#1E3A1E",      # Soft Green BG for additions
            "diff_remove": "#3A1E1E",   # Soft Red BG for deletions
        }

        # Apply background configuration to main root
        self.root.configure(bg=self.colors["bg_main"])

        # Configure styled elements
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
        """Construct the split-screen Google Jules-style layout."""
        # =====================================================================
        # 1. TOP HEADER & CONTROL PANEL
        # =====================================================================
        header_frame = tk.Frame(self.root, bg=self.colors["bg_card"], height=65)
        header_frame.pack(fill="x", padx=10, pady=5)

        header_label = tk.Label(
            header_frame,
            text="🦅  SHARROWKYN",
            font=("Consolas", 18, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["accent_pink"],
        )
        header_label.pack(side="left", padx=15, pady=10)

        sub_label = tk.Label(
            header_frame,
            text="COGNITIVE CO-PILOT",
            font=("Consolas", 9, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["fg_main"],
        )
        sub_label.pack(side="left", padx=5, pady=18)

        self.status_indicator = tk.Label(
            header_frame,
            text="💤 LEGIONNAIRE IDLE",
            font=("Consolas", 10, "bold"),
            bg=self.colors["bg_input"],
            fg=self.colors["neon_cyan"],
            padx=12,
            pady=4,
        )
        self.status_indicator.pack(side="right", padx=15, pady=10)

        # =====================================================================
        # 2. INPUT PANEL (Workspace & Task Prompt)
        # =====================================================================
        input_frame = tk.Frame(self.root, bg=self.colors["bg_main"])
        input_frame.pack(fill="x", padx=10, pady=5)

        # Workspace
        path_label = tk.Label(
            input_frame,
            text="📁 WORKSPACE:",
            font=("Consolas", 9, "bold"),
            bg=self.colors["bg_main"],
            fg=self.colors["fg_main"],
        )
        path_label.grid(row=0, column=0, sticky="w", padx=5, pady=3)

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
        self.path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3)

        # Task
        prompt_label = tk.Label(
            input_frame,
            text="🎯 TASK OBJECTIVE:",
            font=("Consolas", 9, "bold"),
            bg=self.colors["bg_main"],
            fg=self.colors["fg_main"],
        )
        prompt_label.grid(row=1, column=0, sticky="w", padx=5, pady=3)

        self.prompt_entry = tk.Entry(
            input_frame,
            font=("Consolas", 11),
            bg=self.colors["bg_card"],
            fg=self.colors["fg_main"],
            insertbackground=self.colors["fg_main"],
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["bg_input"],
            highlightcolor=self.colors["accent_pink"],
        )
        self.prompt_entry.insert(0, "Исправь баг с путями на Windows в storage.py")
        self.prompt_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=3)

        # Launch Button
        self.launch_btn = tk.Button(
            input_frame,
            text="🚀 RUN SHARROWKYN",
            font=("Consolas", 10, "bold"),
            bg=self.colors["accent_pink"],
            fg="#FFFFFF",
            activebackground=self.colors["neon_purple"],
            activeforeground="#FFFFFF",
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2",
            command=self.start_agent,
        )
        self.launch_btn.grid(row=0, column=2, rowspan=2, sticky="ns", padx=10, pady=3)

        input_frame.columnconfigure(1, weight=1)

        # =====================================================================
        # 3. SPLIT MAIN DASHBOARD PANELS (Google Jules Style!)
        # =====================================================================
        # Slidable split-pane layout
        self.pane = tk.PanedWindow(
            self.root,
            orient="horizontal",
            bg=self.colors["bg_main"],
            bd=0,
            sashwidth=4,
            sashrelief="flat",
        )
        self.pane.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Left Panel: Plan Step-List & Thought Log ---
        left_frame = tk.Frame(self.pane, bg=self.colors["bg_card"])
        self.pane.add(left_frame, minsize=380, width=440)

        # Step checklist
        steps_label = tk.Label(
            left_frame,
            text="📝 AGENT COGNITIVE PLAN",
            font=("Consolas", 9, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["accent_pink"],
        )
        steps_label.pack(anchor="w", padx=15, pady=8)

        self.step_labels: list[tk.Label] = []
        step_names = [
            "1. Observe Workspace & AST Structures",
            "2. Recall Memories & DSM context",
            "3. Reason & Draft Code Patches",
            "4. Verify Stability (pytest tests)",
            "5. Commit changes to s-git & DSM",
        ]

        for name in step_names:
            lbl = tk.Label(
                left_frame,
                text=f"⏳ {name}",
                font=("Consolas", 9),
                bg=self.colors["bg_card"],
                fg=self.colors["fg_main"],
                anchor="w",
            )
            lbl.pack(fill="x", padx=25, pady=2)
            self.step_labels.append(lbl)

        # Thought Log Terminal
        log_label = tk.Label(
            left_frame,
            text="💬 THOUGHTS & EXECUTION LOG",
            font=("Consolas", 9, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["neon_cyan"],
        )
        log_label.pack(anchor="w", padx=15, pady=(15, 5))

        self.log_area = ScrolledText(
            left_frame,
            font=("Consolas", 9),
            bg=self.colors["bg_main"],
            fg=self.colors["fg_main"],
            bd=0,
            insertbackground=self.colors["fg_main"],
            highlightthickness=1,
            highlightbackground=self.colors["bg_input"],
        )
        self.log_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # --- Right Panel: Real-time Code Diff-Viewer ---
        right_frame = tk.Frame(self.pane, bg=self.colors["bg_card"])
        self.pane.add(right_frame, minsize=420, width=620)

        diff_label = tk.Label(
            right_frame,
            text="🛠️ ACTIVE CODE DIFF-VIEWER",
            font=("Consolas", 9, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["neon_green"],
        )
        diff_label.pack(anchor="w", padx=15, pady=8)

        self.diff_area = ScrolledText(
            right_frame,
            font=("Consolas", 9),
            bg=self.colors["bg_main"],
            fg=self.colors["fg_main"],
            bd=0,
            insertbackground=self.colors["fg_main"],
            highlightthickness=1,
            highlightbackground=self.colors["bg_input"],
        )
        self.diff_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Config tags for Diff syntax coloring
        self.diff_area.tag_config("add", background=self.colors["diff_add"], foreground="#98C379")
        self.diff_area.tag_config("remove", background=self.colors["diff_remove"], foreground="#E06C75")
        self.diff_area.tag_config("header", foreground=self.colors["neon_purple"], font=("Consolas", 9, "bold"))
        self.diff_area.tag_config("info", foreground=self.colors["neon_cyan"])

        # Config tags for Log terminal coloring
        self.log_area.tag_config("info", foreground=self.colors["neon_cyan"])
        self.log_area.tag_config("success", foreground=self.colors["neon_green"])
        self.log_area.tag_config("warning", foreground=self.colors["neon_yellow"])
        self.log_area.tag_config("error", foreground=self.colors["accent_pink"], font=("Consolas", 9, "bold"))
        self.log_area.tag_config("system", foreground=self.colors["neon_purple"], font=("Consolas", 9, "bold"))

    def update_step(self, step_idx: int, status: str) -> None:
        """Thread-safe update of the visual checklist indicators."""
        label = self.step_labels[step_idx]
        original_text = label.cget("text")[2:]  # Remove the icon

        if status == "active":
            label.config(text=f"🔄 {original_text}", fg=self.colors["accent_pink"], font=("Consolas", 9, "bold"))
        elif status == "done":
            label.config(text=f"✅ {original_text}", fg=self.colors["neon_green"], font=("Consolas", 9))
        else:
            label.config(text=f"⏳ {original_text}", fg=self.colors["fg_main"], font=("Consolas", 9))

    def reset_steps(self) -> None:
        for i in range(len(self.step_labels)):
            self.update_step(i, "idle")

    def pipe_log(self, text: str, tag: str = "default") -> None:
        """Thread-safe logging pipe into the styled console panel."""
        self.log_area.insert("end", text + "\n", tag)
        self.log_area.see("end")

    def pipe_diff(self, diff_text: str) -> None:
        """Stream diff lines into the right viewer panel, dynamically syntax-coloring."""
        self.diff_area.delete("1.0", "end")
        lines = diff_text.splitlines()
        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                self.diff_area.insert("end", line + "\n", "add")
            elif line.startswith("-") and not line.startswith("---"):
                self.diff_area.insert("end", line + "\n", "remove")
            elif line.startswith("@@") or line.startswith("---") or line.startswith("+++"):
                self.diff_area.insert("end", line + "\n", "header")
            else:
                self.diff_area.insert("end", line + "\n")
        self.diff_area.see("end")

    def start_agent(self) -> None:
        """Trigger agent thread to prevent GUI freezing."""
        workspace = self.path_entry.get().strip()
        task = self.prompt_entry.get().strip()

        if not workspace or not task:
            messagebox.showwarning("Warning", "Please enter workspace path and task prompt.")
            return

        self.launch_btn.config(state="disabled", bg=self.colors["bg_input"])
        self.status_indicator.config(text="🧠 WRAITH-SLIP ACTIVE", fg=self.colors["accent_pink"])
        self.log_area.delete("1.0", "end")
        self.diff_area.delete("1.0", "end")
        self.reset_steps()

        agent_thread = threading.Thread(
            target=self.run_agent_cycle,
            args=(workspace, task),
            daemon=True,
        )
        agent_thread.start()

    def run_agent_cycle(self, workspace: str, task: str) -> None:
        """Thread run logic."""
        agent = SharoukinAgent(
            workspace,
            log_callback=self.pipe_log,
            step_callback=lambda idx, stat: self.root.after(0, self.update_step, idx, stat),
            diff_callback=lambda diff: self.root.after(0, self.pipe_diff, diff),
        )
        success = agent.execute_task(task)
        self.root.after(0, self.agent_completed, success)

    def agent_completed(self, success: bool) -> None:
        self.launch_btn.config(state="normal", bg=self.colors["accent_pink"])
        if success:
            self.status_indicator.config(text="✔ COGNITION SECURED", fg=self.colors["neon_green"])
        else:
            self.status_indicator.config(text="❌ INVARIANT CRASHED", fg=self.colors["accent_pink"])


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    root = tk.Tk()
    app = SharoukinDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
