"""
PanicButton — The Developer's Emergency Exit for Cryptic Stack Traces.

Paste a messy terminal error, send it to an LLM (Gemini or OpenAI),
and get a plain English explanation + a direct code fix.
Supports AICC (universal), Google Gemini, and OpenAI backends.

Author : PanicButton Team
Created: 2026-05-03
"""

# ─────────────────────────── standard library ───────────────────────────
import os
import sys
import abc
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, font as tkfont
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

# ── Tell Windows this is its own app (so taskbar shows our icon, not Python's) ──
try:
    # 1. Separate taskbar grouping
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "PanicButton.DebugAssistant.1.0"
    )
    # 2. Enable DPI awareness (fixes blurry text and blurry header logo on Windows scaling)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except (AttributeError, OSError):
    pass  # non-Windows or older OS — safe to ignore

# ─────────────────────────── third-party ────────────────────────────────
from dotenv import load_dotenv
import pyperclip

# ─────────────────────────── load .env early ────────────────────────────
load_dotenv()

# ─────────────────────────── paths ──────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_LOGO_PNG   = _SCRIPT_DIR / "PanicButtonlogo_circle.png"
_LOGO_ICO   = _SCRIPT_DIR / "PanicButton.ico"


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 1 — Modular AI Backend (Strategy Pattern)
# ═══════════════════════════════════════════════════════════════════════

# The exact system prompt mandated by the project spec.
SYSTEM_PROMPT = (
    "You are an expert debugging assistant. The user will provide a raw "
    "stack trace or terminal error. You must respond in exactly two sections. "
    "Section 1: 'Root Cause:' Provide a single, plain English sentence "
    "explaining exactly why the error occurred. "
    "Section 2: 'Suggested Fix:' Provide the exact code snippet required to "
    "resolve the issue. Do not include any greeting, markdown formatting "
    "outside of code blocks, conclusion, or conversational filler."
)


class AIBackend(abc.ABC):
    """Abstract base class for all LLM backends."""

    @abc.abstractmethod
    def query(self, user_message: str) -> str:
        """Send *user_message* to the LLM and return the response text."""
        ...


class GeminiBackend(AIBackend):
    """Google Gemini (google-generativeai) backend."""

    def __init__(self, api_key: str):
        import google.generativeai as genai          # lazy import
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name="gemini-3-pro-preview",
            system_instruction=SYSTEM_PROMPT,
        )

    def query(self, user_message: str) -> str:
        response = self._model.generate_content(user_message)
        return response.text


class AICCBackend(AIBackend):
    """AICC universal API backend (OpenAI-compatible, any model)."""

    AICC_BASE_URL = "https://api.ai.cc/v1"

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI                    # lazy import
        self._client = OpenAI(api_key=api_key, base_url=self.AICC_BASE_URL)
        self._model = model

    def query(self, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content


class OpenAIBackend(AIBackend):
    """OpenAI (GPT) backend — swap-in alternative."""

    def __init__(self, api_key: str):
        from openai import OpenAI                    # lazy import
        self._client = OpenAI(api_key=api_key)

    def query(self, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content


def create_backend() -> AIBackend | None:
    """
    Factory: pick the right backend based on which API key is present.
    Priority: AICC_API_KEY  ▸  GEMINI_API_KEY  ▸  OPENAI_API_KEY
    Returns None if no key is found.
    """
    aicc_key   = os.getenv("AICC_API_KEY", "").strip()
    aicc_model = os.getenv("AICC_MODEL", "gpt-4o").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if aicc_key:
        return AICCBackend(aicc_key, model=aicc_model)
    if gemini_key:
        return GeminiBackend(gemini_key)
    if openai_key:
        return OpenAIBackend(openai_key)
    return None


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 2 — Theme Definitions
# ═══════════════════════════════════════════════════════════════════════

DARK_THEME = {
    "name":         "dark",
    "bg":           "#1a1a2e",           # deep navy
    "bg_secondary": "#16213e",           # slightly lighter panel
    "bg_input":     "#0f3460",           # input field background
    "fg":           "#e0e0e0",           # main text
    "fg_dim":       "#8892a4",           # subtle / placeholder text
    "accent":       "#e94560",           # panic-red accent
    "accent_hover": "#ff6b6b",           # lighter on hover
    "btn_fg":       "#ffffff",
    "border":       "#233554",
    "success":      "#00d2ff",           # copy-success flash
    "selection_bg": "#e94560",
    "selection_fg": "#ffffff",
}

LIGHT_THEME = {
    "name":         "light",
    "bg":           "#f5f5f7",
    "bg_secondary": "#ffffff",
    "bg_input":     "#ffffff",
    "fg":           "#1d1d1f",
    "fg_dim":       "#6e6e73",
    "accent":       "#d63031",
    "accent_hover": "#e17055",
    "btn_fg":       "#ffffff",
    "border":       "#d1d1d6",
    "success":      "#00b894",
    "selection_bg": "#d63031",
    "selection_fg": "#ffffff",
}


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 3 — The Main Application Window
# ═══════════════════════════════════════════════════════════════════════

class PanicButtonApp(tk.Tk):
    """Top-level Tkinter window for PanicButton."""

    # ─────────────── construction ───────────────
    def __init__(self):
        super().__init__()

        # --- window basics ---
        self.title("PanicButton 🚨")
        self.geometry("640x680")
        self.minsize(560, 600)
        self.configure(bg=DARK_THEME["bg"])

        # --- state ---
        self._theme = DARK_THEME                    # start in dark mode
        self._backend: AIBackend | None = None       # set after UI is drawn
        self._is_busy = False                        # prevent double-clicks

        # --- window icon (taskbar + title bar) ---
        self._logo_photo = None      # keep reference so GC doesn't eat it
        self._header_logo = None
        try:
            if _LOGO_ICO.exists():
                self.iconbitmap(default=str(_LOGO_ICO))
        except tk.TclError:
            pass  # graceful fallback if icon fails

        try:
            if _LOGO_PNG.exists():
                from PIL import Image, ImageTk
                _pil = Image.open(str(_LOGO_PNG))
                
                # header logo (make it larger: 64x64 instead of 40x40 for clarity)
                _header = _pil.resize((64, 64), Image.LANCZOS)
                self._header_logo = ImageTk.PhotoImage(_header)
                
                # Provide multiple sizes so Windows can pick the sharpest one for taskbar/titlebar
                self._icon_photos = [
                    ImageTk.PhotoImage(_pil.resize((size, size), Image.LANCZOS))
                    for size in (256, 128, 64, 32, 16)
                ]
                self.iconphoto(True, *self._icon_photos)
        except Exception:
            pass  # Pillow not installed or image missing — text fallback

        # --- fonts ---
        self._title_font = tkfont.Font(family="Segoe UI", size=18, weight="bold")
        self._label_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self._mono_font  = tkfont.Font(family="Consolas", size=10)
        self._btn_font   = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self._small_font = tkfont.Font(family="Segoe UI", size=9)

        # --- build UI ---
        self._build_header()
        self._build_input_section()
        self._build_action_section()
        self._build_output_section()
        self._build_footer()

        # --- try to initialise AI backend ---
        try:
            self._backend = create_backend()
        except Exception as exc:
            self._set_output(f"⚠️  Failed to initialise AI backend:\n{exc}")

        if self._backend is None:
            self._set_output(
                "⚠️  No API key found!\n\n"
                "Create a .env file in the project root with one of:\n\n"
                "  AICC_API_KEY=your-key-here      (universal, recommended)\n"
                "  GEMINI_API_KEY=your-key-here\n"
                "  OPENAI_API_KEY=your-key-here\n\n"
                "Then restart the application."
            )

        # --- apply the initial theme consistently ---
        self._apply_theme()

    # ─────────────── header (title + theme toggle) ───────────────
    def _build_header(self):
        """Create the top bar with app title and dark/light toggle."""
        self._header = tk.Frame(self, bg=self._theme["bg"])
        self._header.pack(fill="x", padx=20, pady=(18, 6))

        # Logo image in header (if available)
        if self._header_logo:
            self._logo_label = tk.Label(
                self._header,
                image=self._header_logo,
                bg=self._theme["bg"],
            )
            self._logo_label.pack(side="left", padx=(0, 8))
        else:
            self._logo_label = None

        # App title
        self._title_label = tk.Label(
            self._header,
            text="PanicButton",
            font=self._title_font,
            fg=self._theme["accent"],
            bg=self._theme["bg"],
        )
        self._title_label.pack(side="left")

        # Subtitle
        self._subtitle_label = tk.Label(
            self._header,
            text="decode errors instantly",
            font=self._small_font,
            fg=self._theme["fg_dim"],
            bg=self._theme["bg"],
        )
        self._subtitle_label.pack(side="left", padx=(10, 0), pady=(6, 0))

        # Theme toggle button
        self._theme_btn = tk.Button(
            self._header,
            text="☀️ Light",
            font=self._small_font,
            fg=self._theme["fg"],
            bg=self._theme["bg_secondary"],
            activebackground=self._theme["bg_secondary"],
            activeforeground=self._theme["fg"],
            bd=0,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right")

        # About Developer button
        self._about_btn = tk.Button(
            self._header,
            text="ℹ️",
            font=self._small_font,
            fg=self._theme["fg"],
            bg=self._theme["bg_secondary"],
            activebackground=self._theme["bg_secondary"],
            activeforeground=self._theme["fg"],
            bd=0,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._show_about,
        )
        self._about_btn.pack(side="right", padx=(0, 10))

    # ─────────────── input section ───────────────
    def _build_input_section(self):
        """The 'Paste Stack Trace / Error' label + ScrolledText."""
        frame = tk.Frame(self, bg=self._theme["bg"])
        frame.pack(fill="both", expand=True, padx=20, pady=(8, 4))

        self._input_label = tk.Label(
            frame,
            text="Paste Stack Trace / Error:",
            font=self._label_font,
            fg=self._theme["fg"],
            bg=self._theme["bg"],
            anchor="w",
        )
        self._input_label.pack(fill="x")

        self._input_frame = tk.Frame(frame, bg=self._theme["border"], bd=1, relief="solid")
        self._input_frame.pack(fill="both", expand=True, pady=(4, 0))

        self._input_text = ScrolledText(
            self._input_frame,
            font=self._mono_font,
            bg=self._theme["bg_input"],
            fg=self._theme["fg"],
            insertbackground=self._theme["fg"],
            selectbackground=self._theme["selection_bg"],
            selectforeground=self._theme["selection_fg"],
            relief="flat",
            wrap="word",
            height=8,
            bd=8,
        )
        self._input_text.pack(fill="both", expand=True)

    # ─────────────── action section (Decode button) ───────────────
    def _build_action_section(self):
        """The prominent 'Decode Error' button."""
        action_frame = tk.Frame(self, bg=self._theme["bg"])
        action_frame.pack(fill="x", padx=20, pady=8)

        self._decode_btn = tk.Button(
            action_frame,
            text="⚡  Decode Error",
            font=self._btn_font,
            fg=self._theme["btn_fg"],
            bg=self._theme["accent"],
            activebackground=self._theme["accent_hover"],
            activeforeground=self._theme["btn_fg"],
            bd=0,
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self._on_decode,
        )
        self._decode_btn.pack(fill="x")

        # Hover effects
        self._decode_btn.bind("<Enter>", lambda e: self._decode_btn.configure(bg=self._theme["accent_hover"]))
        self._decode_btn.bind("<Leave>", lambda e: self._decode_btn.configure(bg=self._theme["accent"]))

    # ─────────────── output section ───────────────
    def _build_output_section(self):
        """The AI response display (read-only but selectable)."""
        frame = tk.Frame(self, bg=self._theme["bg"])
        frame.pack(fill="both", expand=True, padx=20, pady=(4, 8))

        self._output_label = tk.Label(
            frame,
            text="AI Response:",
            font=self._label_font,
            fg=self._theme["fg"],
            bg=self._theme["bg"],
            anchor="w",
        )
        self._output_label.pack(fill="x")

        self._output_frame = tk.Frame(frame, bg=self._theme["border"], bd=1, relief="solid")
        self._output_frame.pack(fill="both", expand=True, pady=(4, 0))

        self._output_text = ScrolledText(
            self._output_frame,
            font=self._mono_font,
            bg=self._theme["bg_secondary"],
            fg=self._theme["fg"],
            insertbackground=self._theme["bg_secondary"],
            selectbackground=self._theme["selection_bg"],
            selectforeground=self._theme["selection_fg"],
            relief="flat",
            wrap="word",
            height=8,
            state="disabled",
            bd=8,
        )
        self._output_text.pack(fill="both", expand=True)

    # ─────────────── footer (utility buttons) ───────────────
    def _build_footer(self):
        """Bottom row: Copy Fix · Clear All."""
        self._footer = tk.Frame(self, bg=self._theme["bg"])
        self._footer.pack(fill="x", padx=20, pady=(0, 18))

        self._copy_btn = tk.Button(
            self._footer,
            text="📋  Copy Fix to Clipboard",
            font=self._small_font,
            fg=self._theme["fg"],
            bg=self._theme["bg_secondary"],
            activebackground=self._theme["border"],
            activeforeground=self._theme["fg"],
            bd=0,
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._on_copy,
        )
        self._copy_btn.pack(side="left", padx=(0, 8))

        self._clear_btn = tk.Button(
            self._footer,
            text="🗑️  Clear All",
            font=self._small_font,
            fg=self._theme["fg"],
            bg=self._theme["bg_secondary"],
            activebackground=self._theme["border"],
            activeforeground=self._theme["fg"],
            bd=0,
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._on_clear,
        )
        self._clear_btn.pack(side="left")

        # Status label (right-aligned, shows copy confirmation etc.)
        self._status_label = tk.Label(
            self._footer,
            text="",
            font=self._small_font,
            fg=self._theme["success"],
            bg=self._theme["bg"],
        )
        self._status_label.pack(side="right")

    # ═══════════════════════════════════════════════════════════════
    #  Theme management
    # ═══════════════════════════════════════════════════════════════

    def _toggle_theme(self):
        """Switch between dark and light themes."""
        if self._theme["name"] == "dark":
            self._theme = LIGHT_THEME
        else:
            self._theme = DARK_THEME
        self._apply_theme()

    def _apply_theme(self):
        """Re-colour every widget to match the current theme dict."""
        t = self._theme

        self.configure(bg=t["bg"])

        # Header
        self._header.configure(bg=t["bg"])
        if self._logo_label:
            self._logo_label.configure(bg=t["bg"])
        self._title_label.configure(fg=t["accent"], bg=t["bg"])
        self._subtitle_label.configure(fg=t["fg_dim"], bg=t["bg"])
        self._theme_btn.configure(
            text="☀️ Light" if t["name"] == "dark" else "🌙 Dark",
            fg=t["fg"],
            bg=t["bg_secondary"],
            activebackground=t["bg_secondary"],
            activeforeground=t["fg"],
        )
        self._about_btn.configure(
            fg=t["fg"],
            bg=t["bg_secondary"],
            activebackground=t["bg_secondary"],
            activeforeground=t["fg"],
        )

        # Input section
        self._input_label.master.configure(bg=t["bg"])
        self._input_label.configure(fg=t["fg"], bg=t["bg"])
        self._input_frame.configure(bg=t["border"])
        self._input_text.configure(
            bg=t["bg_input"],
            fg=t["fg"],
            insertbackground=t["fg"],
            selectbackground=t["selection_bg"],
            selectforeground=t["selection_fg"],
        )

        # Decode button
        self._decode_btn.master.configure(bg=t["bg"])
        self._decode_btn.configure(
            fg=t["btn_fg"],
            bg=t["accent"],
            activebackground=t["accent_hover"],
            activeforeground=t["btn_fg"],
        )
        # Re-bind hover colours
        self._decode_btn.bind("<Enter>", lambda e: self._decode_btn.configure(bg=t["accent_hover"]))
        self._decode_btn.bind("<Leave>", lambda e: self._decode_btn.configure(bg=t["accent"]))

        # Output section
        self._output_label.master.configure(bg=t["bg"])
        self._output_label.configure(fg=t["fg"], bg=t["bg"])
        self._output_frame.configure(bg=t["border"])
        self._output_text.configure(
            bg=t["bg_secondary"],
            fg=t["fg"],
            insertbackground=t["bg_secondary"],
            selectbackground=t["selection_bg"],
            selectforeground=t["selection_fg"],
        )

        # Footer
        self._footer.configure(bg=t["bg"])
        for btn in (self._copy_btn, self._clear_btn):
            btn.configure(
                fg=t["fg"],
                bg=t["bg_secondary"],
                activebackground=t["border"],
                activeforeground=t["fg"],
            )
        self._status_label.configure(fg=t["success"], bg=t["bg"])

    # ═══════════════════════════════════════════════════════════════
    #  Core actions
    # ═══════════════════════════════════════════════════════════════

    def _set_output(self, text: str):
        """Helper: overwrite the output box content (handles disabled state)."""
        self._output_text.configure(state="normal")
        self._output_text.delete("1.0", "end")
        self._output_text.insert("1.0", text)
        self._output_text.configure(state="disabled")

    def _flash_status(self, message: str, duration_ms: int = 2500):
        """Show a temporary status message in the footer."""
        self._status_label.configure(text=message)
        self.after(duration_ms, lambda: self._status_label.configure(text=""))

    # ── Decode Error ──
    def _on_decode(self):
        """Validate input, show loading state, fire LLM call in a thread."""
        if self._is_busy:
            return

        # Grab input
        raw = self._input_text.get("1.0", "end").strip()
        if not raw:
            self._flash_status("⚠️  Paste an error first!", 2000)
            return

        if self._backend is None:
            self._set_output(
                "⚠️  No AI backend configured.\n\n"
                "Add your API key to .env and restart."
            )
            return

        # Enter loading state
        self._is_busy = True
        self._decode_btn.configure(state="disabled", text="⏳  Analyzing…")
        self._set_output("Analyzing stack trace… please wait.")

        # Run the API call off the main thread
        thread = threading.Thread(target=self._call_llm, args=(raw,), daemon=True)
        thread.start()

    def _call_llm(self, user_message: str):
        """(Runs in a background thread) Query the LLM and post result."""
        try:
            result = self._backend.query(user_message)
        except Exception as exc:
            result = (
                f"❌  API call failed:\n\n{type(exc).__name__}: {exc}\n\n"
                "Check your internet connection and API key, then try again."
            )

        # Schedule the UI update back on the main thread
        self.after(0, self._on_llm_done, result)

    def _on_llm_done(self, result: str):
        """Callback on the main thread after the LLM responds."""
        self._set_output(result)
        self._decode_btn.configure(state="normal", text="⚡  Decode Error")
        self._is_busy = False

    # ── Copy Fix ──
    def _on_copy(self):
        """Copy the output text to the system clipboard via pyperclip."""
        content = self._output_text.get("1.0", "end").strip()
        if not content:
            self._flash_status("Nothing to copy.", 1500)
            return
        try:
            pyperclip.copy(content)
            self._flash_status("✅  Copied to clipboard!")
        except Exception:
            self._flash_status("⚠️  Clipboard unavailable.")

    # ── Clear All ──
    def _on_clear(self):
        """Clear both input and output fields."""
        self._input_text.delete("1.0", "end")
        self._set_output("")
        self._flash_status("Cleared.", 1200)

    # ── About Developer ──
    def _show_about(self):
        """Display the developer profile in a popup window."""
        about_win = tk.Toplevel(self)
        about_win.title("About Developer")
        about_win.geometry("540x600")
        about_win.minsize(400, 400)
        about_win.configure(bg=self._theme["bg"])
        
        # Make the popup modal
        about_win.transient(self)
        about_win.grab_set()

        try:
            if hasattr(self, '_logo_photo') and self._logo_photo:
                about_win.iconphoto(False, self._logo_photo)
        except Exception:
            pass

        frame = tk.Frame(about_win, bg=self._theme["bg"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        text_widget = ScrolledText(
            frame,
            font=self._small_font,
            bg=self._theme["bg_secondary"],
            fg=self._theme["fg"],
            relief="flat",
            wrap="word",
            padx=12,
            pady=12,
            bd=1
        )
        text_widget.pack(fill="both", expand=True)

        # Define fonts
        title_f = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        header_f = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        bold_f = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        italic_f = tkfont.Font(family="Segoe UI", size=9, slant="italic")

        # Configure tags
        text_widget.tag_configure("title", font=title_f, justify="center", foreground=self._theme["accent"])
        text_widget.tag_configure("header", font=header_f, foreground=self._theme["accent"], spacing1=10, spacing3=5)
        text_widget.tag_configure("bold", font=bold_f)
        text_widget.tag_configure("italic", font=italic_f)
        text_widget.tag_configure("bullet", lmargin1=20, lmargin2=35, spacing1=2)
        text_widget.tag_configure("center", justify="center")
        text_widget.tag_configure("quote", font=italic_f, lmargin1=30, rmargin=30, justify="center", foreground=self._theme["fg_dim"])
        text_widget.tag_configure("contact", font=bold_f, foreground=self._theme["success"])

        # Insert formatted content
        def insert(text, tags=""):
            text_widget.insert("end", text, tags)

        insert("🧠 Muhammad Ali\n", "title")
        insert("Professional Profile\n\n", "center")

        insert("Contact Information\n", "header")
        insert("📧 Email: ", "bold")
        insert("nawabzadaalimirza56@gmail.com\n", "contact")
        insert("🐙 GitHub: ", "bold")
        insert("Muhammad-Ali-56\n\n", "contact")

        insert("👤 Identity\n", "header")
        insert("Name: ", "bold"); insert("Muhammad Ali\n")
        insert("Role: ", "bold"); insert("Software Engineer | AI & Machine Learning Engineer\n")
        insert("Core Domain: ", "bold"); insert("Intelligent Systems, Scalable Software Architecture, Applied AI\n")

        insert("🚀 Executive Summary\n", "header")
        insert("Muhammad Ali is a highly technical software engineer specializing in Artificial Intelligence (AI) and Machine Learning (ML) systems. He operates at the intersection of software engineering discipline and data-driven intelligence, focusing on designing, building, and deploying scalable, production-grade intelligent applications.\n\n")
        insert("His engineering approach is system-oriented, emphasizing:\n")
        insert(" • Clean architecture\n", "bullet")
        insert(" • Performance optimization\n", "bullet")
        insert(" • Real-world applicability of AI models\n", "bullet")
        insert(" • End-to-end ownership (from data to deployment)\n", "bullet")

        insert("🧩 Core Competencies\n", "header")
        insert("1. 💻 Software Engineering\n", "bold")
        insert("Strong command over:\n")
        insert(" • Data structures & algorithms\n", "bullet")
        insert(" • System design (distributed systems, microservices)\n", "bullet")
        insert(" • Backend development (APIs, services, pipelines)\n", "bullet")
        insert("Focus on: ", "bold"); insert("Scalability, Maintainability, Reliability under load\n\n")

        insert("2. 🤖 AI & Machine Learning\n", "bold")
        insert("Expertise in: ", "bold"); insert("Supervised/Unsupervised Learning, Deep Learning (CNNs, RNNs, Transformers), Model optimization and tuning.\n")
        insert("Experience with: ", "bold"); insert("Model training pipelines, Feature engineering, Evaluation metrics and validation strategies.\n\n")

        insert("3. ⚙️ System Architecture\n", "bold")
        insert("Designs end-to-end ML systems, including: ", "bold"); insert("Data ingestion pipelines, Model serving infrastructure, Real-time vs batch processing systems.\n")
        insert("Example architecture pattern:\n")
        insert("[ Data Source ] → [ ETL Pipeline ] → [ Feature Store ] →\n[ Model Training ] → [ Model Registry ] →\n[ API / Inference Layer ] → [ Monitoring ]\n\n", "center")

        insert("4. 📊 Data Engineering Awareness\n", "bold")
        insert("Handles: ", "bold"); insert("Data preprocessing at scale, Data cleaning pipelines, Efficient storage (SQL / NoSQL).\n\n")

        insert("5. ☁️ Deployment & DevOps (ML Ops)\n", "bold")
        insert("Familiar with: ", "bold"); insert("Containerization (Docker), CI/CD pipelines.\n")
        insert("Model deployment strategies: ", "bold"); insert("REST APIs, Batch inference, Streaming inference.\n")

        insert("🧠 Engineering Philosophy\n", "header")
        insert("“Build systems that solve real problems, not just models that look good on paper.”\n\n", "quote")
        insert("Key principles:\n")
        insert(" • Prefer simple, scalable solutions over complex prototypes.\n", "bullet")
        insert(" • Optimize for production readiness, not just experimentation.\n", "bullet")
        insert(" • Treat AI models as components in larger systems, not standalone artifacts.\n", "bullet")

        insert("📈 Potential Specialization Directions\n", "header")
        insert("🔹 AI Systems Engineering (high demand)\n", "bullet")
        insert("🔹 LLM Applications & Prompt Engineering\n", "bullet")
        insert("🔹 Computer Vision Systems\n", "bullet")
        insert("🔹 Real-time ML (streaming inference systems)\n", "bullet")
        insert("🔹 AI SaaS product development\n", "bullet")

        insert("🧭 Suggested Personal Brand Positioning\n", "header")
        insert("“AI Systems Engineer building scalable, production-grade intelligent applications.”\n", "quote")

        text_widget.configure(state="disabled")

        btn_frame = tk.Frame(about_win, bg=self._theme["bg"])
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        close_btn = tk.Button(
            btn_frame,
            text="Close",
            font=self._btn_font,
            fg=self._theme["btn_fg"],
            bg=self._theme["accent"],
            activebackground=self._theme["accent_hover"],
            activeforeground=self._theme["btn_fg"],
            bd=0,
            relief="flat",
            padx=20,
            pady=6,
            cursor="hand2",
            command=about_win.destroy
        )
        close_btn.pack(side="right")
        close_btn.bind("<Enter>", lambda e: close_btn.configure(bg=self._theme["accent_hover"]))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(bg=self._theme["accent"]))


# ═══════════════════════════════════════════════════════════════════════
#  SECTION 4 — Entry point
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = PanicButtonApp()
    app.mainloop()
