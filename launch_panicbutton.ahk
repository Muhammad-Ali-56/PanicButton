; ──────────────────────────────────────────────────
;  PanicButton — Global Hotkey Launcher (AutoHotkey v1)
; ──────────────────────────────────────────────────
;  Shortcut:  Ctrl + Shift + P
;  Action:    Launch panicbutton main.py from any window.
;
;  Instructions:
;    1. Install AutoHotkey from https://www.autohotkey.com
;    2. Update the path below to point to YOUR project folder.
;    3. Double-click this .ahk file (or add it to Startup).
; ──────────────────────────────────────────────────

#NoEnv
#SingleInstance Force
SetWorkingDir %A_ScriptDir%

; ── Ctrl + Shift + P  ▸  Launch PanicButton ──
^+p::
    ; Update this path if your project lives elsewhere
    ProjectDir := "C:\Users\alipa\Desktop\PanicButton"
    Run, pythonw "%ProjectDir%\main.py", %ProjectDir%
    return
