import os
import sys
import time
import threading
import whisper
from moviepy.editor import VideoFileClip
from datetime import timedelta

# Kivy imports
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line

# KivyMD imports
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.textfield import MDTextField

class Transcriber:
    """Klasa odpowiedzialna za transkrypcję audio do tekstu"""
    
    # Dostępne modele Whisper i ich opisy
    AVAILABLE_MODELS = {
        "tiny": "Najszybszy, najmniej dokładny",
        "base": "Szybki, podstawowa dokładność",
        "small": "Zbalansowany (szybkość/dokładność)",
        "medium": "Dobra dokładność, wolniejszy",
        "large": "Najdokładniejszy, najwolniejszy"
    }
    
    # Dostępne języki
    AVAILABLE_LANGUAGES = {
        "pl": "Polski",
        "en": "Angielski",
        "de": "Niemiecki",
        "fr": "Francuski",
        "es": "Hiszpański",
        "it": "Włoski",
        "ru": "Rosyjski",
        "uk": "Ukraiński",
        "cs": "Czeski",
        "sk": "Słowacki"
    }
    
    def __init__(self):
        self.model = None
        self.model_name = "large"  # Używamy najdokładniejszego modelu dla języka polskiego
        self.language = "pl"
        self.progress_callback = None
        self.status_callback = None
        self.cancel_flag = False
    
    def set_callbacks(self, progress_callback=None, status_callback=None):
        """Ustawia funkcje callback do raportowania postępu"""
        self.progress_callback = progress_callback
        self.status_callback = status_callback
    
    def set_model(self, model_name):
        """Ustawia model Whisper"""
        if model_name in self.AVAILABLE_MODELS:
            self.model_name = model_name
            self.model = None  # Resetujemy załadowany model, aby wymusić ponowne załadowanie
            return True
        return False
    
    def set_language(self, language):
        """Ustawia język transkrypcji"""
        if language in self.AVAILABLE_LANGUAGES:
            self.language = language
            return True
        return False
        
    def cancel(self):
        """Ustawia flagę anulowania operacji"""
        self.cancel_flag = True
    
    def update_status(self, message):
        """Aktualizuje status operacji"""
        print(message)
        if self.status_callback:
            self.status_callback(message)
    
    def update_progress(self, progress):
        """Aktualizuje postęp operacji (0-100)"""
        if self.progress_callback:
            self.progress_callback(progress)
    
    def format_time(self, seconds):
        """Konwertuje sekundy do formatu czasu SRT (HH:MM:SS,mmm)"""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int(td.microseconds / 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def extract_audio(self, video_path, output_path="temp_audio.wav"):
        """Wyodrębnia audio z pliku wideo"""
        self.update_status(f"Wyodrębnianie audio z pliku wideo: {video_path}")
        try:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(output_path, codec='pcm_s16le', verbose=False, logger=None)
            self.update_status(f"Audio wyodrębnione pomyślnie: {output_path}")
            return output_path
        except Exception as e:
            self.update_status(f"Błąd podczas wyodrębniania audio: {e}")
            raise
    
    def load_model(self):
        """Ładuje model Whisper"""
        if self.model is None:
            self.update_status(f"Ładowanie modelu Whisper {self.model_name}...")
            self.model = whisper.load_model(self.model_name)
            self.update_status(f"Model Whisper {self.model_name} załadowany pomyślnie")
            return True
        return False
    
    def transcribe_audio(self, audio_path, language=None):
        """Transkrybuje audio za pomocą Whisper"""
        self.cancel_flag = False
        
        if language is not None:
            self.language = language
        
        self.load_model()
        
        self.update_status(f"Rozpoczęcie transkrypcji z użyciem Whisper (model: {self.model_name}, język: {self.language})...")
        result = self.model.transcribe(audio_path, language=self.language, verbose=False)
        
        # Konwersja segmentów Whisper do naszego formatu
        transcription = []
        total_segments = len(result["segments"])
        
        for i, segment in enumerate(result["segments"]):
            if self.cancel_flag:
                self.update_status("Transkrypcja anulowana przez użytkownika")
                return None
                
            transcription.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            })
            progress = int((i + 1) / total_segments * 100)
            self.update_progress(progress)
            self.update_status(f"Transkrypcja segmentu {i+1}/{total_segments}: Udana")
        
        self.update_status("Transkrypcja zakończona pomyślnie")
        return transcription
    
    def create_srt_file(self, transcription, output_file):
        """Tworzy plik SRT z danych transkrypcji"""
        self.update_status(f"Tworzenie pliku SRT: {output_file}")
        with open(output_file, "w", encoding="utf-8") as f:
            for i, segment in enumerate(transcription):
                # SRT index
                f.write(f"{i+1}\n")
                
                # Time codes
                start_time = self.format_time(segment["start"])
                end_time = self.format_time(segment["end"])
                f.write(f"{start_time} --> {end_time}\n")
                
                # Text
                f.write(f"{segment['text']}\n\n")
        
        self.update_status(f"Plik SRT został utworzony: {output_file}")
        return output_file
    
    def process_video(self, video_path, output_file=None):
        """Przetwarza plik wideo do pliku SRT"""
        start_time = time.time()
        self.cancel_flag = False
        
        # Ustawienie domyślnej ścieżki wyjściowej, jeśli nie podano
        if not output_file or not output_file.strip():
            base_name = os.path.splitext(video_path)[0]
            output_file = f"{base_name}.srt"
        
        try:
            # Wyodrębnienie audio z wideo
            if self.cancel_flag:
                self.update_status("Operacja anulowana przez użytkownika")
                return None
                
            audio_path = self.extract_audio(video_path)
            
            # Transkrypcja audio
            if self.cancel_flag:
                self.update_status("Operacja anulowana przez użytkownika")
                return None
                
            transcription = self.transcribe_audio(audio_path)
            if transcription is None:  # Anulowano podczas transkrypcji
                return None
            
            # Utworzenie pliku SRT
            if self.cancel_flag:
                self.update_status("Operacja anulowana przez użytkownika")
                return None
                
            self.create_srt_file(transcription, output_file)
            
            elapsed_time = time.time() - start_time
            self.update_status(f"Transkrypcja zakończona pomyślnie! Utworzono plik: {output_file}")
            self.update_status(f"Całkowity czas wykonania: {elapsed_time:.2f} sekund")
            
            return output_file
        except Exception as e:
            self.update_status(f"Błąd: {str(e)}")
            raise
        finally:
            # Usunięcie tymczasowego pliku audio
            if 'audio_path' in locals() and os.path.exists(audio_path):
                os.remove(audio_path)
                self.update_status("Usunięto tymczasowy plik audio")

class TranscriberGUI(MDBoxLayout):
    """Główny interfejs użytkownika aplikacji"""
    
    def __init__(self, **kwargs):
        super(TranscriberGUI, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [20, 20, 20, 20]  # Jednolite marginesy
        self.spacing = 15  # Zwiększony odstęp między elementami
        self.md_bg_color = [0.1, 0.1, 0.12, 1]  # Tło dla całego interfejsu
        
        self.transcriber = Transcriber()
        self.selected_file = None
        self.output_file = None
        self.transcription_thread = None
        self.file_manager = None
        
        # Główna karta z całą zawartością
        self.main_card = MDCard(
            orientation="vertical",
            padding=(20, 40, 20, 20),  # Jeszcze bardziej zwiększony padding górny
            size_hint=(0.95, 0.92),  # Bardziej zmniejszona wysokość karty
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            elevation=4,
            md_bg_color=(0.1, 0.1, 0.12, 1)
        )
        
        # Tytuł aplikacji
        self.title_label = MDLabel(
            text="Automatyczna transkrypcja plików wideo",
            halign="center",
            font_style="H5",
            size_hint_y=None,
            height=70,  # Jeszcze bardziej zwiększona wysokość etykiety tytułu
            theme_text_color="Custom",
            text_color=(0.9, 0.9, 0.9, 1),
            padding=(0, 10, 0, 0)  # Dodatkowy padding górny
        )
        self.main_card.add_widget(self.title_label)
        
        # Opis aplikacji
        self.description_label = MDLabel(
            text="",
            halign="center",
            size_hint_y=None,
            height=40,  # Zmniejszona wysokość
            theme_text_color="Secondary",
            font_style="Subtitle1"
        )
        self.main_card.add_widget(self.description_label)
        
        # Separator po tytule
        self.separator1 = BoxLayout(
            size_hint_y=None,
            height=2,
            padding=(0, 15, 0, 15),  # Zwiększony padding
            pos_hint={"center_x": 0.5}  # Wycentrowanie w poziomie
        )
        with self.separator1.canvas:
            Color(0.3, 0.3, 0.3, 1)
            Rectangle(pos=self.separator1.pos, size=self.separator1.size)
        self.main_card.add_widget(self.separator1)
        
        # Inicjalizacja file managera - nie będziemy go używać, zamiast tego użyjemy eksploratora Windows
        
        # Sekcja wyboru pliku wejściowego i wyjściowego
        self.file_section = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=220,  # Zwiększona wysokość sekcji dla dodatkowego pola
            spacing=10,  # Zmniejszony odstęp
            padding=[0, 10, 0, 10]
        )
        
        # Nagłówek sekcji
        self.file_section_header = MDLabel(
            text="WYBIERZ PLIKI",
            halign="center",
            size_hint_y=None,
            height=20,
            bold=True,
            theme_text_color="Primary"
        )
        self.file_section.add_widget(self.file_section_header)
        
        # Wybór pliku wejściowego - pole tekstowe z przyciskiem eksploratora
        self.file_input_label = MDLabel(
            text="Plik wideo wejściowy:",
            size_hint_y=None,
            height=20,
            theme_text_color="Secondary"
        )
        self.file_section.add_widget(self.file_input_label)
        
        self.file_input_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=50,
            spacing=10
        )
        
        # Pole tekstowe w stylu MDTextField dla pliku wejściowego
        self.file_input = MDTextField(
            hint_text="Ścieżka do pliku wideo",
            helper_text="Wprowadź ścieżkę lub kliknij 'Przeglądaj'",
            helper_text_mode="on_focus",
            multiline=False,
            size_hint_x=0.8
        )
        self.file_input.bind(text=self.on_file_input_change)
        self.file_input_layout.add_widget(self.file_input)
        
        # Przycisk eksploratora dla pliku wejściowego
        self.browse_button = MDRaisedButton(
            text="Przeglądaj",
            on_release=self.open_file_manager,
            size_hint_x=0.2,
            md_bg_color=self.theme_cls.accent_color
        )
        self.file_input_layout.add_widget(self.browse_button)
        
        self.file_section.add_widget(self.file_input_layout)
        
        # Wybór pliku wyjściowego - pole tekstowe z przyciskiem eksploratora
        self.output_file_label = MDLabel(
            text="Plik napisów wyjściowy:",
            size_hint_y=None,
            height=20,
            theme_text_color="Secondary"
        )
        self.file_section.add_widget(self.output_file_label)
        
        self.output_file_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=50,
            spacing=10
        )
        
        # Pole tekstowe w stylu MDTextField dla pliku wyjściowego
        self.output_file_input = MDTextField(
            hint_text="Ścieżka do pliku SRT",
            helper_text="Wprowadź ścieżkę lub kliknij 'Przeglądaj'",
            helper_text_mode="on_focus",
            multiline=False,
            size_hint_x=0.8
        )
        self.output_file_layout.add_widget(self.output_file_input)
        
        # Przycisk eksploratora dla pliku wyjściowego
        self.output_browse_button = MDRaisedButton(
            text="Przeglądaj",
            on_release=self.open_output_file_manager,
            size_hint_x=0.2,
            md_bg_color=self.theme_cls.accent_color
        )
        self.output_file_layout.add_widget(self.output_browse_button)
        
        self.file_section.add_widget(self.output_file_layout)
        
        # Informacja o wybranych plikach
        self.selected_file_label = MDLabel(
            text="Nie wybrano plików",
            halign="center",
            size_hint_y=None,
            height=20,
            theme_text_color="Secondary",
            font_style="Caption"
        )
        self.file_section.add_widget(self.selected_file_label)
        
        self.main_card.add_widget(self.file_section)
        
        # Separator (linia pozioma)
        self.separator2 = BoxLayout(
            size_hint_y=None,
            height=2,
            padding=[5, 5, 5, 5]
        )
        # Dodajemy kolor tła do separatora
        with self.separator2.canvas.before:
            Color(0.3, 0.3, 0.3, 1)
            Rectangle(pos=self.separator2.pos, size=self.separator2.size)
        self.main_card.add_widget(self.separator2)
        

        
        # Sekcja opcji transkrypcji
        self.options_section = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=150,
            spacing=10,
            padding=[0, 10, 0, 10]
        )
        
        # Nagłówek sekcji opcji
        self.options_section_header = MDLabel(
            text="OPCJE TRANSKRYPCJI",
            halign="center",
            size_hint_y=None,
            height=30,
            bold=True,
            theme_text_color="Primary"
        )
        self.options_section.add_widget(self.options_section_header)
        
        # Opcje transkrypcji - dropdowny
        self.options_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=100,
            spacing=20
        )
        
        # Wybór języka
        self.language_layout = MDBoxLayout(
            orientation="vertical",
            size_hint_x=0.5,
            spacing=5
        )
        
        self.language_label = MDLabel(
            text="Język transkrypcji:",
            size_hint_y=None,
            height=20,
            theme_text_color="Secondary"
        )
        self.language_layout.add_widget(self.language_label)
        
        # Dropdown języka
        self.language_dropdown = DropDown()
        self.language_dropdown.background_color = [0.2, 0.2, 0.25, 1]
        
        for lang_code, lang_name in self.transcriber.AVAILABLE_LANGUAGES.items():
            btn = Button(
                text=f"{lang_name} ({lang_code})",
                size_hint_y=None,
                height=44,
                background_color=[0.25, 0.25, 0.3, 1],
                background_normal="",
                color=[0.9, 0.9, 0.9, 1]
            )
            btn.bind(on_release=lambda btn, lang_code=lang_code: self.select_language(lang_code, btn.text))
            self.language_dropdown.add_widget(btn)
        
        self.language_button = Button(
            text="Polski (pl)",
            size_hint_y=None,
            height=50,
            background_color=[0.3, 0.3, 0.35, 1],
            background_normal="",
            color=[0.9, 0.9, 0.9, 1]
        )
        self.language_button.bind(on_release=self.language_dropdown.open)
        self.language_layout.add_widget(self.language_button)
        
        self.options_layout.add_widget(self.language_layout)
        
        # Wybór modelu
        self.model_layout = MDBoxLayout(
            orientation="vertical",
            size_hint_x=0.5,
            spacing=5
        )
        
        self.model_label = MDLabel(
            text="Siła transkrypcji (model):",
            size_hint_y=None,
            height=20,
            theme_text_color="Secondary"
        )
        self.model_layout.add_widget(self.model_label)
        
        # Dropdown modelu
        self.model_dropdown = DropDown()
        self.model_dropdown.background_color = [0.2, 0.2, 0.25, 1]
        
        for model_name, model_desc in self.transcriber.AVAILABLE_MODELS.items():
            btn = Button(
                text=f"{model_name} - {model_desc}",
                size_hint_y=None,
                height=44,
                background_color=[0.25, 0.25, 0.3, 1],
                background_normal="",
                color=[0.9, 0.9, 0.9, 1]
            )
            btn.bind(on_release=lambda btn, model=model_name: self.select_model(model, btn.text))
            self.model_dropdown.add_widget(btn)
        
        self.model_button = Button(
            text="large - Najdokładniejszy, najwolniejszy",
            size_hint_y=None,
            height=50,
            background_color=[0.3, 0.3, 0.35, 1],
            background_normal="",
            color=[0.9, 0.9, 0.9, 1]
        )
        self.model_button.bind(on_release=self.model_dropdown.open)
        self.model_layout.add_widget(self.model_button)
        
        self.options_layout.add_widget(self.model_layout)
        
        self.options_section.add_widget(self.options_layout)
        self.main_card.add_widget(self.options_section)
        
        # Separator (linia pozioma)
        self.separator3 = BoxLayout(
            size_hint_y=None,
            height=2,
            padding=[5, 5, 5, 5]
        )
        # Dodajemy kolor tła do separatora
        with self.separator3.canvas.before:
            Color(0.3, 0.3, 0.3, 1)
            Rectangle(pos=self.separator3.pos, size=self.separator3.size)
        self.main_card.add_widget(self.separator3)
        
        # Sekcja postępu
        self.progress_section = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=150,
            spacing=10,
            padding=[0, 10, 0, 10]
        )
        
        # Nagłówek sekcji postępu
        self.progress_section_header = MDLabel(
            text="STATUS TRANSKRYPCJI",
            halign="center",
            size_hint_y=None,
            height=30,
            bold=True,
            theme_text_color="Primary"
        )
        self.progress_section.add_widget(self.progress_section_header)
        
        # Pasek postępu - asynchroniczny
        self.progress_bar = MDProgressBar(
            value=0,
            size_hint_y=None,
            height=15,
            color=self.theme_cls.accent_color,
            running_duration=1,
            catching_duration=1.5
        )
        self.progress_section.add_widget(self.progress_bar)
        
        # Status transkrypcji
        self.status_label = MDLabel(
            text="Gotowy do transkrypcji",
            halign="center",
            size_hint_y=None,
            height=30,
            theme_text_color="Primary",
            font_style="Subtitle1"
        )
        self.progress_section.add_widget(self.status_label)
        
        # Dodatkowy label dla informacji o modelu i języku
        self.info_label = MDLabel(
            text="Model: large | Język: Polski (pl)",
            halign="center",
            size_hint_y=None,
            height=30,
            theme_text_color="Secondary",
            font_style="Caption"
        )
        self.progress_section.add_widget(self.info_label)
        
        self.main_card.add_widget(self.progress_section)
        
        # Separator (linia pozioma)
        self.separator4 = BoxLayout(
            size_hint_y=None,
            height=2,
            padding=[5, 5, 5, 5]
        )
        # Dodajemy kolor tła do separatora
        with self.separator4.canvas.before:
            Color(0.3, 0.3, 0.3, 1)
            Rectangle(pos=self.separator4.pos, size=self.separator4.size)
        self.main_card.add_widget(self.separator4)
        
        # Sekcja przycisków akcji
        self.buttons_section = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=100,
            spacing=10,
            padding=[0, 20, 0, 10]
        )
        
        # Przyciski akcji
        self.buttons_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=60,
            spacing=20,
            padding=[20, 0, 20, 0]
        )
        
        self.transcribe_button = MDRaisedButton(
            text="ROZPOCZNIJ TRANSKRYPCJĘ",
            on_release=self.start_transcription,
            disabled=True,
            size_hint_x=0.6,
            height=50,
            md_bg_color=self.theme_cls.primary_color,
            elevation=4,
            font_style="Button"
        )
        self.buttons_layout.add_widget(self.transcribe_button)
        
        self.cancel_button = MDRaisedButton(
            text="ANULUJ",
            on_release=self.cancel_transcription,
            disabled=True,
            md_bg_color=[0.8, 0.2, 0.2, 1],
            size_hint_x=0.4,
            height=50,
            elevation=4,
            font_style="Button"
        )
        self.buttons_layout.add_widget(self.cancel_button)
        
        self.buttons_section.add_widget(self.buttons_layout)
        self.main_card.add_widget(self.buttons_section)
        
        # Dodanie głównej karty do interfejsu
        self.add_widget(self.main_card)
        
        # Ustawienie callbacków dla Transcribera
        self.transcriber.set_callbacks(
            progress_callback=self.update_progress,
            status_callback=self.update_status
        )
    
    def on_file_input_change(self, instance, value):
        """Obsługa zmiany tekstu w polu ścieżki pliku wejściowego"""
        if os.path.isfile(value):
            self.selected_file = value
            filename = os.path.basename(self.selected_file)
            
            # Ustaw domyślną ścieżkę wyjściową i zaktualizuj pole
            base_name = os.path.splitext(self.selected_file)[0]
            self.output_file = f"{base_name}.srt"
            self.output_file_input.text = self.output_file
            
            # Aktualizuj etykietę informacyjną
            self.selected_file_label.text = f"Wejście: {filename} | Wyjście: {os.path.basename(self.output_file)}"
            self.update_transcribe_button_state()
        else:
            self.selected_file = None
            self.update_transcribe_button_state()
            self.selected_file_label.text = "Nieprawidłowa ścieżka pliku wejściowego"
    
    def open_file_manager(self, instance):
        """Otwiera eksplorator Windows do wyboru pliku wejściowego"""
        import tkinter as tk
        from tkinter import filedialog
        
        # Ukryj główne okno Tkinter
        root = tk.Tk()
        root.withdraw()
        
        # Otwieranie eksploratora Windows
        file_types = [
            ("Pliki wideo", "*.mp4;*.avi;*.mkv;*.mov;*.wmv"),
            ("Wszystkie pliki", "*.*")
        ]
        path = filedialog.askopenfilename(
            title="Wybierz plik wideo wejściowy",
            filetypes=file_types,
            initialdir=os.path.expanduser("~")
        )
        
        # Obsługa wybranego pliku
        if path and os.path.isfile(path):
            self.file_input.text = path
            self.selected_file = path
            filename = os.path.basename(path)
            
            # Ustaw domyślną ścieżkę wyjściową i zaktualizuj pole
            base_name = os.path.splitext(self.selected_file)[0]
            self.output_file = f"{base_name}.srt"
            self.output_file_input.text = self.output_file
            
            # Aktualizuj etykietę informacyjną
            self.selected_file_label.text = f"Wejście: {filename} | Wyjście: {os.path.basename(self.output_file)}"
            self.update_transcribe_button_state()
        
        # Zniszcz obiekt Tkinter
        root.destroy()
    
    def open_output_file_manager(self, instance):
        """Otwiera eksplorator Windows do wyboru pliku wyjściowego"""
        import tkinter as tk
        from tkinter import filedialog
        
        # Ukryj główne okno Tkinter
        root = tk.Tk()
        root.withdraw()
        
        # Otwieranie eksploratora Windows
        file_types = [
            ("Pliki napisów SRT", "*.srt"),
            ("Wszystkie pliki", "*.*")
        ]
        
        # Ustal domyślną nazwę pliku
        default_filename = ""
        if self.selected_file:
            base_name = os.path.splitext(self.selected_file)[0]
            default_filename = f"{os.path.basename(base_name)}.srt"
        
        # Ustal domyślny katalog
        initial_dir = os.path.expanduser("~")
        if self.selected_file:
            initial_dir = os.path.dirname(self.selected_file)
        
        path = filedialog.asksaveasfilename(
            title="Wybierz plik napisów wyjściowy",
            filetypes=file_types,
            initialdir=initial_dir,
            initialfile=default_filename,
            defaultextension=".srt"
        )
        
        # Obsługa wybranego pliku
        if path:
            self.output_file = path
            self.output_file_input.text = path
            
            # Aktualizuj etykietę informacyjną
            if self.selected_file:
                input_filename = os.path.basename(self.selected_file)
                output_filename = os.path.basename(path)
                self.selected_file_label.text = f"Wejście: {input_filename} | Wyjście: {output_filename}"
            else:
                self.selected_file_label.text = f"Wyjście: {os.path.basename(path)}"
            
            self.update_transcribe_button_state()
        
        # Zniszcz obiekt Tkinter
        root.destroy()
    
    def update_transcribe_button_state(self):
        """Aktualizuje stan przycisku transkrypcji na podstawie wybranych plików"""
        # Przycisk jest aktywny tylko jeśli wybrano plik wejściowy
        self.transcribe_button.disabled = not self.selected_file
    
    def select_language(self, lang_code, lang_text):
        """Obsługa wyboru języka z dropdown"""
        self.transcriber.set_language(lang_code)
        self.language_button.text = lang_text
        self.language_dropdown.dismiss()
        self.update_info_label()
    
    def select_model(self, model_name, model_text):
        """Obsługa wyboru modelu z dropdown"""
        self.transcriber.set_model(model_name)
        self.model_button.text = model_text
        self.model_dropdown.dismiss()
        self.update_info_label()
    
    def update_info_label(self):
        """Aktualizuje etykietę informacyjną"""
        lang_code = self.transcriber.language
        lang_name = self.transcriber.AVAILABLE_LANGUAGES.get(lang_code, "Nieznany")
        self.info_label.text = f"Model: {self.transcriber.model_name} | Język: {lang_name} ({lang_code})"
    
    def update_progress(self, value):
        """Aktualizuje pasek postępu"""
        def update(dt):
            self.progress_bar.value = value
        Clock.schedule_once(update, 0)
    
    def update_progress_async(self, dt):
        """Asynchronicznie aktualizuje pasek postępu z efektem płynności"""
        if not self.transcription_thread or not self.transcription_thread.is_alive():
            # Jeśli transkrypcja zakończona, zatrzymaj aktualizację
            Clock.unschedule(self.update_progress_async)
            return
        
        # Dodaj efekt płynności - lekkie wahania paska postępu
        import random
        if self.progress_bar.value < 100:
            # Dodaj niewielkie losowe wahania do paska postępu
            if random.random() < 0.3:  # 30% szans na aktualizację
                current = self.progress_bar.value
                # Niewielki przyrost, ale nie więcej niż 1%
                increment = random.uniform(0, 0.5)
                self.progress_bar.value = min(current + increment, 100)
    
    def update_status(self, message):
        """Aktualizuje etykietę statusu"""
        def update(dt):
            self.status_label.text = message
        Clock.schedule_once(update, 0)
    
    def start_transcription(self, instance):
        """Rozpoczyna proces transkrypcji w osobnym wątku"""
        if self.selected_file:
            # Aktualizacja UI
            self.transcribe_button.disabled = True
            self.cancel_button.disabled = False
            self.progress_bar.value = 0
            self.update_status("Przygotowanie do transkrypcji...")
            
            # Uruchomienie transkrypcji w osobnym wątku
            self.transcription_thread = threading.Thread(
                target=self.run_transcription,
                args=(self.selected_file, self.output_file)
            )
            self.transcription_thread.daemon = True
            self.transcription_thread.start()
            
            # Uruchomienie asynchronicznego progress bara
            Clock.schedule_interval(self.update_progress_async, 0.1)
    
    def run_transcription(self, video_path, output_file):
        """Wykonuje transkrypcję w osobnym wątku"""
        try:
            # Użyj ścieżki z pola tekstowego, jeśli jest dostępna
            actual_output_file = self.output_file_input.text if self.output_file_input.text else output_file
            self.transcriber.process_video(video_path, actual_output_file)
            
            # Po zakończeniu transkrypcji
            def on_complete(dt):
                self.transcribe_button.disabled = False
                self.cancel_button.disabled = True
                self.show_completion_dialog(output_file)
            
            Clock.schedule_once(on_complete, 0)
        except Exception as e:
            # Obsługa błędów
            def on_error(dt):
                self.transcribe_button.disabled = False
                self.cancel_button.disabled = True
                self.update_status(f"Błąd: {str(e)}")
                self.show_error_dialog(str(e))
            
            Clock.schedule_once(on_error, 0)
    
    def cancel_transcription(self, instance):
        """Anuluje proces transkrypcji"""
        if self.transcription_thread and self.transcription_thread.is_alive():
            # Ustawienie flagi anulowania w Transcriber
            self.transcriber.cancel()
            self.update_status("Anulowanie transkrypcji (poczekaj na zakończenie bieżącego etapu)...")
            self.cancel_button.disabled = True
    
    def show_completion_dialog(self, output_file):
        """Wyświetla dialog po zakończeniu transkrypcji"""
        dialog = MDDialog(
            title="Transkrypcja zakończona",
            text=f"Plik SRT został utworzony: {output_file}",
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                ),
                MDFlatButton(
                    text="Otwórz folder",
                    on_release=lambda x: self.open_output_folder(output_file)
                )
            ]
        )
        dialog.open()
    
    def show_error_dialog(self, error_message):
        """Wyświetla dialog z błędem"""
        dialog = MDDialog(
            title="Błąd transkrypcji",
            text=f"Wystąpił błąd podczas transkrypcji: {error_message}",
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
    
    def open_output_folder(self, file_path):
        """Otwiera folder zawierający plik wyjściowy"""
        folder_path = os.path.dirname(os.path.abspath(file_path))
        os.startfile(folder_path)


class AutoTranscriberApp(MDApp):
    """Główna klasa aplikacji"""
    
    def build(self):
        # Ustawienia motywu
        self.theme_cls.primary_palette = "BlueGray"  # Główny kolor
        self.theme_cls.accent_palette = "DeepOrange"  # Kolor akcentu
        self.theme_cls.primary_hue = "700"  # Ciemniejszy odcień koloru głównego
        self.theme_cls.theme_style = "Dark"  # Ciemny motyw
        
        # Ustawienia okna
        self.title = "Auto Transcriber"
        Window.size = (1000, 750)  # Jeszcze bardziej zwiększona wysokość okna
        Window.minimum_width, Window.minimum_height = 1000, 750  # Ustaw minimalny rozmiar taki sam jak aktualny
        Window.clearcolor = (0.05, 0.05, 0.07, 1)  # Tło okna aplikacji
        Window.resizable = False  # Zablokuj możliwość zmiany rozmiaru okna
        
        return TranscriberGUI()


def main():
    """Funkcja główna uruchamiająca aplikację"""
    app = AutoTranscriberApp()
    app.run()


if __name__ == "__main__":
    main()
