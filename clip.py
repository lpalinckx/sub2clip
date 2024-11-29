import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QLineEdit, QHBoxLayout, QSpinBox, QWidget, QListWidget, QCheckBox,
    QDoubleSpinBox, QComboBox
)
from PyQt5.QtCore import (Qt)
from PyQt5.QtGui import (QMovie)
import pysubs2
from pathlib import Path
from matplotlib import font_manager
import platform
from ffmpeg import (FFmpeg, FFmpegError)
import unicodedata
from subs.subs import (extract_subs, generate_gif)

from loguru import logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class Sub2Clip(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sub2Clip")
        self.setGeometry(100, 100, 800, 600)

        # Main Layout
        self.main_layout = QVBoxLayout()

        # Video Loader
        self.video_label = QLabel("Selected Video: None")
        self.load_video_button = QPushButton("Load Video")
        self.load_video_button.clicked.connect(self.load_video)
        self.main_layout.addWidget(self.video_label)
        self.main_layout.addWidget(self.load_video_button)

        # Subtitle Search
        self.subtitle_search_input = QLineEdit()
        self.subtitle_search_input.setPlaceholderText("Search subtitles...")
        self.subtitle_search_input.returnPressed.connect(self.search_subtitles)
        self.subtitle_search_button = QPushButton("Search")
        self.subtitle_search_button.clicked.connect(self.search_subtitles)
        self.subtitle_results = QListWidget()
        self.subtitle_results.itemClicked.connect(self.select_search_result)
        subtitle_layout = QHBoxLayout()
        subtitle_layout.addWidget(self.subtitle_search_input)
        subtitle_layout.addWidget(self.subtitle_search_button)
        self.main_layout.addLayout(subtitle_layout)
        self.main_layout.addWidget(self.subtitle_results)

        # Clip Selection
        self.start_time = QDoubleSpinBox()
        self.start_time.setPrefix("Start: ")
        self.start_time.setSuffix(" s")
        self.start_time.setMaximum(9999)
        self.start_time.setSingleStep(1)
        self.start_time.setDecimals(1)
        self.end_time = QDoubleSpinBox()
        self.end_time.setPrefix("End: ")
        self.end_time.setSuffix(" s")
        self.end_time.setDecimals(1)
        self.end_time.setSingleStep(1)
        self.end_time.setMaximum(9999)
        clip_layout = QHBoxLayout()
        clip_layout.addWidget(self.start_time)
        clip_layout.addWidget(self.end_time)
        self.main_layout.addLayout(clip_layout)

        # Custom Text
        self.custom_text_input = QLineEdit()
        self.custom_text_input.setPlaceholderText("Enter custom text for the GIF (optional)...")
        self.main_layout.addWidget(self.custom_text_input)

        # Set fps
        self.fps = QSpinBox()
        self.fps.setPrefix("FPS: ")
        self.fps.setValue(20)
        self.fps.setMaximum(60)

        # Crop to square or not
        self.square_checkbox = QCheckBox("Square GIF (crop sides)")

        # Font size
        self.font_size = QSpinBox()
        self.font_size.setPrefix("Font size: ")
        self.font_size.setValue(24)

        # Set resolution
        self.resolution = QSpinBox()
        self.resolution.setPrefix("Resolution: ")
        self.resolution.setMaximum(1080)
        self.resolution.setValue(320)

        # Layout
        video_settings_layout = QHBoxLayout()
        video_settings_layout.addWidget(self.fps)
        video_settings_layout.addWidget(self.square_checkbox)
        video_settings_layout.addWidget(self.font_size)
        video_settings_layout.addWidget(self.resolution)
        self.main_layout.addLayout(video_settings_layout)

        # Choose font
        if platform.system() == 'Windows':
            self.font_label = QLabel("Font: Arial (default)")
        else:
            self.font_label = QLabel('Font: (default)')

        self.main_layout.addWidget(self.font_label)
        self.font_dropdown = QComboBox()

        ttf = font_manager.fontManager.ttflist
        ttf.sort(key=lambda font: (font.name, font.weight))
        self.font_dict = {}

        for font in ttf:
            font_str = f'{font.name} {font.weight}'
            if font.style != 'normal':
                font_str += f' {font.style}'

            self.font_dropdown.addItem(font_str)
            self.font_dict[font_str] = Path(font.fname)

        self.font_dropdown.currentIndexChanged.connect(self.on_font_select)
        self.main_layout.addWidget(self.font_dropdown)

        # Generate GIF Button
        self.generate_gif_button = QPushButton("Generate GIF")
        self.generate_gif_button.clicked.connect(self.generate_gif)
        self.main_layout.addWidget(self.generate_gif_button)

        # Status
        self.status_label = QLabel("")
        self.main_layout.addWidget(self.status_label)

        # GIF Preview
        self.gif_preview = QLabel("GIF Preview will appear here")
        self.gif_preview.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.gif_preview)

        # Set Layout
        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)

        # Variables
        self.video_file = None
        self.subtitle_file = None
        self.subtitles = []

        if platform.system() == 'Windows':
            self.selected_font_path = Path("C:/Windows/Fonts/arial.ttf")
        else: self.selected_font_path = ''


    def load_video(self):
        self.video_file, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.mkv)")
        if self.video_file:
            self.video_label.setText(f"Selected Video: {os.path.basename(self.video_file)}")
            # Extract subtitles
            subs, success = extract_subs(self.video_file)
            if success:
                logger.success(f'loaded subtitles for {self.video_file}')
                self.subtitles = subs
                self.status_label.setText("Subtitles loaded successfully!")
                self.load_all_subs()
            else:
                logger.error(subs)
                self.status_label.setText("No subtitles found.")


    def on_font_select(self):
        font_str = self.font_dropdown.currentText()
        font_path = self.font_dict[font_str]

        self.font_label.setText(f'Font: {font_str}')
        self.selected_font_path = font_path

    def normalize_string(self, s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        )

    def search_subtitles(self):
        query = self.subtitle_search_input.text().strip()
        if not self.subtitles:
            self.status_label.setText("Please load subtitles")
            return

        if not query:
            self.load_all_subs()
            return

        self.subtitle_results.clear()
        for sub in self.subtitles:
            sub_norm = self.normalize_string(sub.text)
            query_norm = self.normalize_string(query)
            if query_norm.lower() in sub_norm.lower():
                result = f"[{sub.start // 1000}s - {sub.end // 1000}s] {sub.text}"
                self.subtitle_results.addItem(result)


    def load_all_subs(self):
        self.subtitle_results.clear()
        for sub in self.subtitles:
            result = f"[{sub.start // 1000}s - {sub.end // 1000}s] {sub.text}"
            self.subtitle_results.addItem(result)


    def select_search_result(self, item):
        text = item.text()
        subtitle_timing, subtitle_text = text.split(']')
        start, end = subtitle_timing.strip('[]').replace('s','').split(' - ')
        self.start_time.setValue(float(start))
        self.end_time.setValue(float(end))
        self.custom_text_input.setText(subtitle_text)


    def generate_gif(self):
        if not self.video_file:
            self.status_label.setText("Please load a video first.")
            return

        start = self.start_time.value()
        end = self.end_time.value()
        if start >= end:
            self.status_label.setText("Invalid start and end times.")
            return

        output_clip = "output/clip.mp4"
        output_gif = "output/output.gif"
        custom_text = self.custom_text_input.text().strip()

        if not os.path.exists('output/'):
            os.makedirs('output')

        err, ok = generate_gif(
                start,
                end,
                output_clip,
                output_gif,
                custom_text,
                self.video_file,
                self.fps.value(),
                self.square_checkbox.isChecked(),
                self.resolution.value(),
                self.selected_font_path,
                self.font_size.value()
            )

        if ok:
            size_mb = os.path.getsize(output_gif) / (1024 * 1024)
            size_mb = f"{size_mb:.2f}"
            self.status_label.setText(f"GIF generated: {output_gif}, size={size_mb}MB")
            self.preview_gif(output_gif)
            logger.success(f'{output_gif} generated, size={size_mb}MB')
        else:
            self.status_label.setText(f"Something went wrong creating the GIF")
            logger.error(err)

    def preview_gif(self, gif_path):
        self.gif_movie = QMovie(gif_path)
        self.gif_preview.setMovie(self.gif_movie)
        self.gif_movie.start()

    def close(self):
        logger.success("closing...")

# Run the app
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Sub2Clip()
    window.show()

    app.aboutToQuit.connect(window.close)

    sys.exit(app.exec_())
