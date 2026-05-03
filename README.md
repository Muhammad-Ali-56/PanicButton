# PanicButton 🚨

A lightweight Python-based desktop utility designed to help developers instantly troubleshoot terminal errors. PanicButton allows you to send stack traces to an LLM (via a modular AICC API backend, supporting models like Claude Opus 4.6, OpenAI, and Gemini) and get immediate root cause analysis and code fixes.

## ✨ Features

- **Instant Troubleshooting**: Paste your stack trace and instantly get the root cause and actionable code fixes.
- **Global Hotkey (AutoHotkey)**: Launch the app from anywhere on Windows by simply pressing `Ctrl + Shift + P`.
- **Clipboard Integration**: Uses `pyperclip` to make copying and pasting code and errors seamless.
- **Modular API Backend**: Connects to the LLM of your choice using standard API keys configured securely via `.env`.
- **Sleek UI**: Built with Tkinter, featuring a custom high-resolution logo, clean typography, and a polished user interface.

## 🚀 Setup & Installation

### 1. Prerequisites
- **Python 3.8+** installed on your system.
- **AutoHotkey v1** (optional, but required for the global hotkey feature).

### 2. Install Dependencies
Navigate to the project folder and install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the provided template to create your `.env` file:
```bash
cp .env.template .env
```
Open the `.env` file and fill in your preferred API keys (e.g., OpenAI, Gemini, Claude, etc.).

## ⌨️ Global Hotkey Setup (Windows)

To launch PanicButton instantly over any open window:

1. Install [AutoHotkey](https://www.autohotkey.com/).
2. Double-click the `launch_panicbutton.ahk` file.
3. You can now press `Ctrl + Shift + P` at any time to open the PanicButton app.
   
*Tip: Place a shortcut to `launch_panicbutton.ahk` in your Windows `Startup` folder to have the hotkey available automatically every time you boot your computer.*

## 💻 Usage

- **Run Manually**: You can start the app without the hotkey by running:
  ```bash
  pythonw main.py
  ```
  *(Using `pythonw` instead of `python` ensures no annoying terminal window is left running in the background).*
- **Get Help**: Copy an error message or stack trace from your IDE or terminal, open PanicButton, and ask for a fix!
