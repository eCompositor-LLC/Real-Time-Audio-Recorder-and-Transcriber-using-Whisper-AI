import threading
from tkinter import messagebox
import warnings

import torch

from app.core.recorder import AudioRecorder
from app.gui.components.waveform import WaveformVisualizer
from app.gui.components.log_handler import TextBoxLogHandler
recorder = AudioRecorder()

# Suppress specific warning
warnings.filterwarnings(
    "ignore",
    message=(
        "You are using `torch.load` with `weights_only=False`.*"
    ),
)

import tkinter as tk

from app.core.recorder import AudioRecorder
from app.core.transcriber import AudioTranscriber
from app.core.emotion_analyzer import EmotionAnalyzer
from app.core.text_processor import TextProcessor
from app.core.text_analyzer import TextAnalyzer
from app.gui.handlers.export import export_transcription
from app.gui.handlers.audio import start_recording, stop_recording, transcribe_with_progress, rename_audio_file
from app.utils.config import get_styles
from app.gui.handlers.analysis import analyze_emotions, analyze_text_content, set_api_key, summarize_text, query_text
from app.gui.handlers.theme import toggle_theme
import os
import glob
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from app.gui.handlers.files import browse_directory, rename_transcription_file, browse_multiple_files
import logging
# Import tkinterdnd2 but we won't use it
# from tkinterdnd2 import TkinterDnD
import matplotlib
matplotlib.use("TkAgg")
# Suppress FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

styles=get_styles()
current_theme = styles['dark_theme']

# Set default save directory to the current working directory
save_directory = os.getcwd()
logging.info(f"Default save directory set to: {save_directory}")

# Use standard Tk instead of TkinterDnD.Tk()
root = tk.Tk()
# Create a new horizontal frame
main_frame = tk.Frame(root, bg="#2b2b2b")
main_frame.pack(fill=tk.X, padx=10, pady=5)
button_container = tk.Frame(root, bg="#2b2b2b")
button_container.pack(in_=main_frame, side=tk.LEFT, fill=tk.Y)
# Create log box
log_box = tk.Text(button_container, height=8, width=60, wrap=tk.WORD, state=tk.DISABLED, bg="#333333", fg="white", font=("Helvetica", 10))
log_box.pack(pady=5)
rename_transcription_button = tk.Button(
    button_container,
    text="Rename Transcription (Y)",
    command=lambda:rename_transcription_file(Files),
    state=tk.DISABLED,
    **styles['button_style']
)
rename_transcription_button.pack(side=tk.RIGHT, padx=5)

# Setup logging to the log box
log_handler = TextBoxLogHandler(log_box)
log_handler.setLevel(logging.INFO)
logger = logging.getLogger()
logger.addHandler(log_handler)

# Window configuration
root.title("Real-Time Audio Recorder & Whisper AI Transcriber")
root.configure(bg="#2b2b2b")

# Transcription
transcription_frame = tk.Frame(root, bg="#2b2b2b")
transcription_frame.pack(pady=10)
tk.Label(transcription_frame, text="Transcription", bg="#2b2b2b", fg="white", font=("Arial", 14, "bold")).pack()
frame = tk.Frame(transcription_frame, bg="#2b2b2b")
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
scrollbar = tk.Scrollbar(frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
transcription_box = tk.Text(frame, wrap=tk.WORD, bg="#333333", fg="white", font=("Helvetica", 12), width=100, height=10, yscrollcommand=scrollbar.set, padx=10, pady=10)
transcription_box.pack(fill=tk.BOTH, expand=True)
scrollbar.config(command=transcription_box.yview)

# Control Frame
control_frame = tk.Frame(root, bg="#2b2b2b")
control_frame.pack(pady=10)
tk.Label(control_frame, text="Transcription Controls", bg="#2b2b2b", fg="white", font=("Arial", 14, "bold")).pack()

# Initialize Recording dictionary before using it in button commands
Recording = {
    "recorder": recorder,
    "save_directory": save_directory,
    "visualizer": WaveformVisualizer(root),
    "log_box": log_box,
    "transcription_box": transcription_box
}

start_button = tk.Button(
    button_container, 
    text="Start Recording (R)", 
    command=lambda: start_recording(Recording, control_frame), 
    **styles['button_style']
)
start_button.pack(side=tk.LEFT, padx=5)

stop_button = tk.Button(
    button_container,
    text="Stop Recording (S)",
    command=lambda: stop_recording(Recording, transcription_box),
    state=tk.DISABLED,
    **styles['button_style']
)
stop_button.pack(side=tk.LEFT, padx=5)

whisper_button = tk.Button(
    button_container,
    text="Transcribe Audio (T)",
    command=lambda: transcribe_with_progress(save_directory, transcription_box, "openai/whisper-large-v3", root),
    **styles['button_style']
)
whisper_button.pack(side=tk.LEFT, padx=5)

rename_button = tk.Button(
    button_container,
    text="Rename Audio (N)",
    command=lambda: rename_audio_file(save_directory),
    **styles['button_style']
)
rename_button.pack(side=tk.LEFT, padx=5)

export_button = tk.Button(
    button_container,
    text="Export (E)",
    command=lambda: export_transcription(transcription_box, root),
    **styles['button_style']
)
export_button.pack(side=tk.LEFT, padx=5)

theme_button = tk.Button(
    button_container,
    text="Toggle Theme (D)",
    command=lambda: toggle_theme(root, button_container, log_box, transcription_box, control_frame),
    **styles['button_style']
)
theme_button.pack(side=tk.LEFT, padx=5)

analyze_button = tk.Button(
    button_container,
    text="Analyze (A)",
    command=lambda: analyze_emotions(transcription_box),
    **styles['button_style']
)
analyze_button.pack(side=tk.LEFT, padx=5)

content_button = tk.Button(
    button_container,
    text="Content Analysis (C)",
    command=lambda: analyze_text_content(transcription_box),
    **styles['button_style']
)
content_button.pack(side=tk.LEFT, padx=5)

summarize_button = tk.Button(
    button_container,
    text="Summarize (Z)",
    command=lambda: summarize_text(transcription_box),
    **styles['button_style']
)
summarize_button.pack(side=tk.LEFT, padx=5)

query_button = tk.Button(button_container, text="Ask Question", command=lambda:query_text(Analysis), bg="#4caf50", fg="white", font=("Helvetica", 9, "bold"), bd=3)
query_button.pack(side=tk.LEFT, padx=5)

# Update Recording with button references
Recording.update({
    "start_button": start_button,
    "stop_button": stop_button,
    "transcribe_button": whisper_button,
    "rename_audio_button": rename_button,
    "rename_transcription_button": rename_transcription_button,
    "analyze_button": analyze_button
})

Window={"root":root,"save_directory":save_directory,"transcription_box":transcription_box,"control_frame":control_frame}

# Keyboard Shortcuts
root.bind("<r>", lambda event: start_recording(Recording, control_frame))
root.bind("<s>", lambda event: stop_recording(Recording, transcription_box))
root.bind("<t>", lambda event: transcribe_with_progress(save_directory, transcription_box, "openai/whisper-large-v3", root))
root.bind("<n>", lambda event: rename_audio_file(save_directory))
root.bind("<e>", lambda event: export_transcription(transcription_box, root))
root.bind("<d>", lambda event: toggle_theme(root, button_container, log_box, transcription_box, control_frame))
root.bind("<a>", lambda event: analyze_emotions(transcription_box))
root.bind("<c>", lambda event: analyze_text_content(transcription_box))
root.bind("<z>", lambda event: summarize_text(transcription_box))
root.bind("<y>", lambda event: rename_transcription_file(Files))

Files={"transcription_box":transcription_box}
Analysis={"transcription_box":transcription_box}

root.geometry("1200x800")
root.mainloop()
