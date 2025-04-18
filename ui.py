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
from app.gui.handlers.files import browse_directory, rename_transcription_file, browse_multiple_files
from app.gui.layout.dashboard import open_new_dashboard
from app.gui.layout.window import open_annotation_window
from app.gui.components.setup import setup_tkdnd
import logging
import warnings
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import os
from tkinterdnd2 import TkinterDnD
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

root = TkinterDnD.Tk()
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
rename_transcription_button.pack(pady=3)
# Create a frame for transcription
transcription_frame = tk.Frame(root, bg="#2b2b2b")
transcription_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
control_frame = tk.Frame(transcription_frame, bg="#2b2b2b")
control_frame.pack(fill=tk.X, pady=5)
# Create a frame for the text box and scrollbar
text_container = tk.Frame(transcription_frame, bg="#2b2b2b")
text_container.pack(fill=tk.BOTH, expand=True)
# Add scrollbar
scrollbar = tk.Scrollbar(text_container)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
transcribe_button = tk.Button(
    button_container, text="Transcribe (T)", command=lambda:transcribe_with_progress(Recording), state=tk.DISABLED, **styles['button_style']
)
analyze_button = tk.Button(
    button_container, text="Analyze Emotions (E)", command=lambda:analyze_emotions(Analysis), state=tk.DISABLED, **styles['button_style']
)
analyze_button.pack(pady=3)
transcribe_button.pack(pady=3)
# Transcription Box
transcription_box = tk.Text(
    text_container,
    height=12,
    width=50,
    wrap=tk.WORD,
    bg="#333333",
    fg="white",
    font=("Helvetica", 11),
    yscrollcommand=scrollbar.set
)
transcription_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

recorder = AudioRecorder()
transcriber = AudioTranscriber()
emotion_analyzer = EmotionAnalyzer()
text_processor = TextProcessor()  # Will automatically load API key from .env if available
waveform_frame = tk.Frame(root, bg="#2b2b2b")
waveform_frame.pack(in_=main_frame, side=tk.RIGHT, padx=5)
visualizer = WaveformVisualizer(waveform_frame)
text_analyzer = TextAnalyzer()

start_button = tk.Button(
    button_container, text="Start Recording (S)", command=lambda:start_recording(Recording), **styles['button_style']
)
start_button.pack(pady=3)

# translation code start-----------------------------------------------------------------------------------------------------------------------------------------------------------------
MODEL_NAME = "facebook/nllb-200-distilled-600M"  # Faster version of NLLB
device = "cuda" if torch.cuda.is_available() else "cpu"

try:
    print(f"Loading NLLB-200 model ({MODEL_NAME}) on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Failed to load NLLB model: {e}")
    model, tokenizer = None, None

#  Dictionary of Supported Languages (Including Indian Languages)
LANGUAGES = {
    "English": "eng_Latn",
    "French": "fra_Latn",
    "Spanish": "spa_Latn",
    "German": "deu_Latn",
    "Italian": "ita_Latn",
    "Russian": "rus_Cyrl",
    "Chinese": "zho_Hans",
    # Indian Languages
    "Hindi": "hin_Deva",
    "Bengali": "ben_Beng",
    "Tamil": "tam_Taml",
    "Telugu": "tel_Telu",
    "Marathi": "mar_Deva",
    "Gujarati": "guj_Gujr",
    "Punjabi": "pan_Guru",
    "Malayalam": "mal_Mlym",
    "Kannada": "kan_Knda",
    "Odia": "ory_Orya",
    "Urdu": "urd_Arab",
}

#Optimized translation function
def translate_text_nllb(text, src_lang, tgt_lang):
    if model is None or tokenizer is None:
        return "Error: Model not loaded."

    try:
        # Convert language names to model-specific codes
        src_lang_code = LANGUAGES.get(src_lang, "eng_Latn")
        tgt_lang_code = LANGUAGES.get(tgt_lang, "hin_Deva")  # Default to Hindi

        print(f"Translating from {src_lang} ({src_lang_code}) → {tgt_lang} ({tgt_lang_code})")

        #  Set source language in tokenizer
        tokenizer.src_lang = src_lang_code

        # Encode input text
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(device)

        #  Get `forced_bos_token_id` correctly
        tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang_code)

        if tgt_lang_id is None or tgt_lang_id == tokenizer.unk_token_id:
            print(f"Error: Invalid target language ID for {tgt_lang_code}.")
            return "Translation failed: Invalid target language."

        # Generate translation
        with torch.no_grad():
            translated_tokens = model.generate(**inputs, forced_bos_token_id=tgt_lang_id)

        translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
        return translated_text

    except Exception as e:
        print(f"Translation failed: {e}")
        return f"Translation failed: {e}"

#  Translate the output_transcription.txt file
def translate_file(src_lang, tgt_lang):
    save_directory = os.getcwd()
    transcription_file = os.path.join(save_directory, "output_transcription.txt")
    translated_file = os.path.join(save_directory, f"output_transcription_{tgt_lang}.txt")

    if not os.path.exists(transcription_file):
        messagebox.showerror("Error", "No output_transcription file found. Please transcribe some audio first.")
        return

    try:
        with open(transcription_file, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            messagebox.showerror("Error", "The output_transcription.txt file is empty.")
            return

        translated_text = translate_text_nllb(content, src_lang, tgt_lang)

        with open(translated_file, "w", encoding="utf-8") as f:
            f.write(translated_text)

        messagebox.showinfo("Success", f"Translated file saved as output_transcription_{tgt_lang}.txt")

    except Exception as e:
        messagebox.showerror("Error", f"Translation failed: {e}")

#  Asynchronous wrapper to prevent GUI from freezing
def translate_async(src_lang, tgt_lang):
    threading.Thread(target=lambda: translate_file(src_lang, tgt_lang), daemon=True).start()

#  GUI for Translation
def open_translation_dashboard():
    save_directory = os.getcwd()
    transcription_file = os.path.join(save_directory, "output_transcription.txt")

    if not os.path.exists(transcription_file):
        messagebox.showerror("Error", "No transcription file found. Please transcribe some audio first.")
        return

    # Create a new Tkinter window
    dashboard = tk.Toplevel()
    dashboard.title("Translate output_transcription.txt")
    dashboard.geometry("300x300")

    tk.Label(dashboard, text="Translate output_transcription.txt to:").pack(pady=10)

    # Dropdown for source and target languages
    tk.Label(dashboard, text="Source Language:").pack()
    src_lang_var = tk.StringVar(dashboard)
    src_lang_var.set("English")  # Default source language
    src_lang_menu = tk.OptionMenu(dashboard, src_lang_var, *LANGUAGES.keys())
    src_lang_menu.pack(pady=5)

    tk.Label(dashboard, text="Target Language:").pack()
    tgt_lang_var = tk.StringVar(dashboard)
    tgt_lang_var.set("Hindi")  # Default target language
    tgt_lang_menu = tk.OptionMenu(dashboard, tgt_lang_var, *LANGUAGES.keys())
    tgt_lang_menu.pack(pady=5)

    # Button to translate
    translate_btn = tk.Button(dashboard, text="Translate", 
                               command=lambda: translate_async(src_lang_var.get(), tgt_lang_var.get()))
    translate_btn.pack(pady=10)

    dashboard.mainloop()
MODEL_NAME = "facebook/nllb-200-distilled-600M"  # Faster version of NLLB
device = "cuda" if torch.cuda.is_available() else "cpu"

try:
    print(f"Loading NLLB-200 model ({MODEL_NAME}) on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Failed to load NLLB model: {e}")
    model, tokenizer = None, None

#  Dictionary of Supported Languages (Including Indian Languages)
LANGUAGES = {
    "English": "eng_Latn",
    "French": "fra_Latn",
    "Spanish": "spa_Latn",
    "German": "deu_Latn",
    "Italian": "ita_Latn",
    "Russian": "rus_Cyrl",
    "Chinese": "zho_Hans",
    # Indian Languages
    "Hindi": "hin_Deva",
    "Bengali": "ben_Beng",
    "Tamil": "tam_Taml",
    "Telugu": "tel_Telu",
    "Marathi": "mar_Deva",
    "Gujarati": "guj_Gujr",
    "Punjabi": "pan_Guru",
    "Malayalam": "mal_Mlym",
    "Kannada": "kan_Knda",
    "Odia": "ory_Orya",
    "Urdu": "urd_Arab",
}

#  Optimized translation function
def translate_text_nllb(text, src_lang, tgt_lang):
    if model is None or tokenizer is None:
        return "Error: Model not loaded."

    try:
        # Convert language names to model-specific codes
        src_lang_code = LANGUAGES.get(src_lang, "eng_Latn")
        tgt_lang_code = LANGUAGES.get(tgt_lang, "hin_Deva")  # Default to Hindi

        print(f"Translating from {src_lang} ({src_lang_code}) → {tgt_lang} ({tgt_lang_code})")

        # Set source language in tokenizer
        tokenizer.src_lang = src_lang_code

        # Encode input text
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(device)

        #  Get `forced_bos_token_id` correctly
        tgt_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang_code)

        if tgt_lang_id is None or tgt_lang_id == tokenizer.unk_token_id:
            print(f"Error: Invalid target language ID for {tgt_lang_code}.")
            return "Translation failed: Invalid target language."

        # Generate translation
        with torch.no_grad():
            translated_tokens = model.generate(**inputs, forced_bos_token_id=tgt_lang_id)

        translated_text = tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
        return translated_text

    except Exception as e:
        print(f"Translation failed: {e}")
        return f"Translation failed: {e}"

# Translate the output_transcription.txt file
def translate_file(src_lang, tgt_lang):
    save_directory = os.getcwd()
    transcription_file = os.path.join(save_directory, "output_transcription.txt")
    translated_file = os.path.join(save_directory, f"output_transcription_{tgt_lang}.txt")

    if not os.path.exists(transcription_file):
        messagebox.showerror("Error", "No output_transcription file found. Please transcribe some audio first.")
        return

    try:
        with open(transcription_file, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            messagebox.showerror("Error", "The output_transcription.txt file is empty.")
            return

        translated_text = translate_text_nllb(content, src_lang, tgt_lang)

        with open(translated_file, "w", encoding="utf-8") as f:
            f.write(translated_text)

        messagebox.showinfo("Success", f"Translated file saved as output_transcription_{tgt_lang}.txt")

    except Exception as e:
        messagebox.showerror("Error", f"Translation failed: {e}")

# Asynchronous wrapper to prevent GUI from freezing
def translate_async(src_lang, tgt_lang):
    threading.Thread(target=lambda: translate_file(src_lang, tgt_lang), daemon=True).start()

#  GUI for Translation
def open_translation_dashboard():
    save_directory = os.getcwd()
    transcription_file = os.path.join(save_directory, "output_transcription.txt")

    if not os.path.exists(transcription_file):
        messagebox.showerror("Error", "No transcription file found. Please transcribe some audio first.")
        return

    # Create a new Tkinter window
    dashboard = tk.Toplevel()
    dashboard.title("Translate output_transcription.txt")
    dashboard.geometry("300x300")

    tk.Label(dashboard, text="Translate output_transcription.txt to:").pack(pady=10)

    # Dropdown for source and target languages
    tk.Label(dashboard, text="Source Language:").pack()
    src_lang_var = tk.StringVar(dashboard)
    src_lang_var.set("English")  # Default source language
    src_lang_menu = tk.OptionMenu(dashboard, src_lang_var, *LANGUAGES.keys())
    src_lang_menu.pack(pady=5)

    tk.Label(dashboard, text="Target Language:").pack()
    tgt_lang_var = tk.StringVar(dashboard)
    tgt_lang_var.set("Hindi")  # Default target language
    tgt_lang_menu = tk.OptionMenu(dashboard, tgt_lang_var, *LANGUAGES.keys())
    tgt_lang_menu.pack(pady=5)

    # Button to translate
    translate_btn = tk.Button(dashboard, text="Translate", 
                               command=lambda: translate_async(src_lang_var.get(), tgt_lang_var.get()))
    translate_btn.pack(pady=10)

    dashboard.mainloop()

#translation code end

stop_button = tk.Button(
    button_container,
    text="Stop Recording (X)",
    command=lambda:stop_recording(Recording),
    state=tk.DISABLED,
    **styles['button_style']
)
stop_button.pack(pady=3)

rename_audio_button = tk.Button(
    button_container,
    text="Rename Audio (R)",
    command=lambda:rename_audio_file(Recording),
    state=tk.DISABLED,
    **styles['button_style']
)
rename_audio_button.pack(pady=3)

root.title("Audio Recorder & Emotion Analyzer")
root.geometry("1000x900")
root.configure(bg="#2b2b2b")
# root.tk.eval('package require tkdnd')
Recording={"save_directory":save_directory,"recorder":recorder,"visualizer":visualizer,"start_button":start_button,"stop_button":stop_button,"transcribe_button":transcribe_button,"rename_audio_button":rename_audio_button,"rename_transcription_button":rename_transcription_button,"analyze_button":analyze_button,"transcription_box":transcription_box,"log_box":log_box,'root':root,'transcriber':transcriber}
Analysis={'recorder':recorder,'emotion_analyzer':emotion_analyzer,'text_analyzer':text_analyzer,'text_processor':text_processor,'save_directory':save_directory,'transcription_box':transcription_box,'root':root}
Files={"transcriber":transcriber,"transcription_box":transcription_box,"analyze_button":analyze_button,"root":root,"save_directory":save_directory}
# Bind hotkeys
root.bind("<d>", lambda event: browse_directory(Files))
root.bind("<s>", lambda event: start_recording(Recording))
root.bind("<x>", lambda event: stop_recording(Recording))
root.bind("<t>", lambda event: transcribe_with_progress(Recording))
root.bind("<r>", lambda event: rename_audio_file(Recording))
root.bind("<y>", lambda event: rename_transcription_file(Files))
root.bind("<e>", lambda event: analyze_emotions(Analysis))
# Export Transcription Button
export_button = tk.Button(
    waveform_frame,
    text="Export Transcription",
    command=lambda: export_transcription(transcriber),
    bg="#008CBA",
    fg="white",
    font=("Helvetica", 12, "bold"),
    bd=3, width=20,
    height= 1,
    relief=tk.RAISED
)
export_button.pack(pady=3)
# Transcription Label
transcription_label = tk.Label(
    transcription_frame,
    text="Transcription and Analysis",
    bg="#2b2b2b",
    fg="white",
    font=("Helvetica", 12, "bold")
)
transcription_label.pack(pady=5)
# Add hotkey label at the bottom
hotkey_label = tk.Label(
    root,
    text="Hotkeys:\nD - Select Directory | S - Start Recording | X - Stop Recording\nT - Transcribe | R - Rename Audio | Y - Rename Transcription | E - Analyze Emotions",
    bg="#2b2b2b",
    fg="white",
    font=("Helvetica", 10),
)
hotkey_label.pack(pady=5)
# Configure logging to display in the log box
log_handler = TextBoxLogHandler(log_box)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(log_handler)
logging.getLogger().setLevel(logging.DEBUG)
Theme={"root":root,"main_frame":main_frame,"button_container":button_container,"waveform_frame":waveform_frame,"transcription_frame":transcription_frame,"text_container":text_container,"log_box":log_box,"transcription_box":transcription_box,"transcription_label":transcription_label,"hotkey_label":hotkey_label,"control_frame":control_frame,"visualizer":visualizer,'current_theme':current_theme}
theme_button = tk.Button(
    button_container, 
    text="Toggle Theme", 
    command=lambda:toggle_theme(Theme), 
    **styles['button_style']
)
theme_button.pack(pady=3)
browse_button = tk.Button(
    button_container, text="Browse Directory (D)", command=lambda:browse_directory(Files), **styles['button_style']
)
browse_button.pack(pady=3)

# Batch Transcription Button
batch_button = tk.Button(
    button_container, 
    text="Batch Transcription", 
    command=lambda:browse_multiple_files(Files), 
    bg="#FFA500", bd=3, relief=tk.RAISED, width=20,
    height= 1, font=("Helvetica", 12, "bold"), fg="white"
    
)
batch_button.pack(pady=3)

#Usage Dashboard Button
dashboard_button = tk.Button(button_container, text="Usage Dashboard", command=lambda:open_new_dashboard(save_directory,root), **styles['button_style'])
dashboard_button.pack(pady=3)

analyze_text_button = tk.Button(button_container, text="Analyze Text", command=lambda:analyze_text_content(Analysis), bg="#4caf50", fg="white", font=("Helvetica", 9, "bold"), bd=3)
analyze_text_button.pack(side=tk.LEFT, padx=5)

api_key_button = tk.Button(button_container, text="Set API Key", command=lambda:set_api_key(Analysis), bg="#4caf50", fg="white", font=("Helvetica", 9, "bold"), bd=3)
api_key_button.pack(side=tk.LEFT, padx=5)

summarize_button = tk.Button(button_container, text="Summarize", command=lambda:summarize_text(Analysis), bg="#4caf50", fg="white", font=("Helvetica", 9, "bold"), bd=3)
summarize_button.pack(side=tk.LEFT, padx=5)

query_button = tk.Button(button_container, text="Ask Question", command=lambda:query_text(Analysis), bg="#4caf50", fg="white", font=("Helvetica", 9, "bold"), bd=3)
query_button.pack(side=tk.LEFT, padx=5)

Window={"root":root,"save_directory":save_directory,"transcription_box":transcription_box,"control_frame":control_frame}

# translate button
translation_btn = tk.Button(button_container, text="Translate", command=open_translation_dashboard)
translation_btn.pack(side=tk.LEFT, padx=5)

# Annotate Transcription Button
annotate_button = tk.Button(button_container, text="Annotate Transcription", command=lambda:open_annotation_window(Window), bg="#4caf50", fg="white", font=("Helvetica", 9, "bold"), bd=3, relief=tk.RAISED)
annotate_button.pack(pady=3)

scrollbar.config(command=transcription_box.yview)

setup_tkdnd(root)

root.mainloop()