# 🛋️ SHAROUKIN COGNITIVE CO-PILOT: FOUNDATION & TRANSFER DECK

> **To: Devin (Autonomous Software Engineer Agent)**  
> **From: Antigravity (Google DeepMind Team)**  
> **Subject: Implementation of Sharoukin Desktop Developer Agent & LazyStandup Integration**

Welcome, Devin! This directory contains the complete architectural foundation for the **Sharoukin Desktop Developer Agent** and the **LazyStandup AST-Reporter**. 

Your task is to take these robust, fully verified prototypes and elevate them into a production-grade, highly cohesive desktop copilot ecosystem.

---

## 📂 Co-pilot Components

### 1. 🛋️ `lazystandup/` (AST-Level Standup Reporter)
A local-first, zero-telemetry command-line tool that extracts Abstract Syntax Tree (AST) code changes from our custom `s-git` repository database, routes them through LLMs (Ollama Llama3, OpenAI, or Google Gemini), and produces structured Slack-ready Russian standup updates.
*   **Aesthetics:** Powered by `rich` for gorgeous neon cyber-console outputs, spinners, and markdown panels.
*   **clipboard:** Automatically copies compiled reports to the OS clipboard using `pyperclip`.
*   **Engines:** Supports `ollama`, `openai`, `gemini`, and a fast deterministic `offline` mode.

### 2. 🖥️ `sharoukin_desktop/` (Sharoukin Agent UI)
A premium dark-themed (Obsidian/Cyber-neon) desktop application interface that executes the **Field Free-Energy Cognitive Cycle** (Observe $\rightarrow$ Recall $\rightarrow$ Reason $\rightarrow$ Stabilize $\rightarrow$ Commit).
*   **GUI:** Written in highly-styled, thread-safe asynchronous Tkinter (0 external dependencies, completely lightweight).
*   **Logging:** Live scrolling terminal with colorized status lines (purple for system, green for success, cyan for info).
*   **Loop:** Integrates the structured steps of semantic software modifications.

---

## 🎯 Devin's Tasks & Engineering Goals

Please implement the following features sequentially to build a state-of-the-art product:

### 🚀 Task 1: Unify LazyStandup into the Sharoukin Desktop UI
*   Create a **"Standup" tab** or button in the `sharoukin_desktop` GUI.
*   When clicked, it should trigger the `harvest_changes` engine inside `lazystandup` for the last N hours.
*   Render the compiled markdown report directly inside the desktop app's terminal/markdown viewer with a single-click "Copy to Slack" button.

### 🧠 Task 2: Make the Cognitive Agent Loop Real (Active AI Engineer)
Currently, `sharoukin_desktop/src/agent.py` simulates the steps with `time.sleep` mocks. You need to convert this into a **fully active, autonomous agent**!
*   **Active Observations:** Read actual `.py` files inside the target workspace.
*   **Active Reasoning:** Connect the agent to Google Gemini or OpenAI API (reading `GEMINI_API_KEY` / `OPENAI_API_KEY` from environment variables).
*   **Active Execution:** Write planned code patches to files.
*   **Active Stabilization:** Run actual local test suites (e.g. executing `pytest` via `subprocess` and parsing stdout/stderr to capture failures).
*   **Self-Healing Loop:** If a test fails, feed the stack trace back to the LLM, plan a new patch, and repeat until the tests pass!

### 📦 Task 3: Packaging & CLI Integration
*   Write a unified setup file or configure the pyproject configurations so that running `pip install -e .` on the unified workspace registers both `lazystandup` and `sharoukin` globally.
*   Enable `sgit sharoukin` as a direct subcommand within our custom version control system (`s-git`).

---

## 🛠️ Verification & Run Commands
Ensure you verify your changes by compiling and running:
```bash
# Run LazyStandup (Offline mode)
lazystandup --repo <path_to_sgit_repo> --hours 24 --engine offline

# Launch Sharoukin Desktop GUI
python sharoukin_desktop/src/app.py
```

Let's build a software developer tool that makes standard assistants look like history! We trust your elite coding skills, Devin. Go get 'em! 🦾🚀🤜🤛
