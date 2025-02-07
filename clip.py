import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QLineEdit, QHBoxLayout, QSpinBox, QWidget, QListWidget, QCheckBox,
    QDoubleSpinBox, QComboBox, QListWidgetItem
)
from PyQt5.QtCore import (Qt)
from PyQt5.QtGui import (QMovie)
from pathlib import Path
from matplotlib import font_manager
import platform
import unicodedata
from subs.subs import (extract_subs, generate_gif)

from loguru import logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>")

class SubtitleListItem(QListWidgetItem):
    """
    Custom class to show the subtitle in the List widget with the source video stored
    """
    def __init__(self, text, source_video):
        super().__init__(text)
        self.setStatusTip(os.path.basename(source_video))
        self.source_video = source_video

class Sub2Clip(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sub2Clip")
        self.setGeometry(100, 100, 800, 600)

        # Main Layout
        self.main_layout = QVBoxLayout()

        # Video Loader
        btn_layout = QHBoxLayout()
        self.video_label = QLabel("Selected Video: None")
        self.load_video_button = QPushButton("Load Video")
        self.load_video_button.clicked.connect(self.load_video)
        self.main_layout.addWidget(self.video_label)
        btn_layout.addWidget(self.load_video_button)

        # Directory loader
        self.load_dir_button = QPushButton("Load Directory")
        self.load_dir_button.clicked.connect(self.load_directory)
        btn_layout.addWidget(self.load_dir_button)
        self.main_layout.addLayout(btn_layout)

        # Video dropdown
        self.video_dropdown = QComboBox()
        self.video_dropdown.setEnabled(False)
        self.video_dropdown.addItem('All videos')
        self.video_dropdown.currentIndexChanged.connect(self.on_video_select)
        self.main_layout.addWidget(self.video_dropdown)

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

        # Caption
        self.caption_text_input = QLineEdit()
        self.caption_text_input.setPlaceholderText("Enter a caption (optional)")
        self.main_layout.addWidget(self.caption_text_input)

        # Set fps
        self.fps = QSpinBox()
        self.fps.setPrefix("FPS: ")
        self.fps.setValue(20)
        self.fps.setMaximum(60)

        # Crop to square or not
        self.square_checkbox = QCheckBox("Square GIF (crop sides)")

        # Fancy colors (larger GIF size)
        self.fancy_colors_checkbox = QCheckBox("Fancy colors")

        # Create boomerang gif?
        self.boomerang_checkbox = QCheckBox("Boomerang GIF")

        # Also create mp4 with HC subs? (mp4s have better compression)
        self.mp4_copy_checkbox = QCheckBox("MP4 with subs")

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
        video_settings_layout.addWidget(self.boomerang_checkbox)
        video_settings_layout.addWidget(self.fancy_colors_checkbox)
        video_settings_layout.addWidget(self.mp4_copy_checkbox)
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


    def load_directory(self):
        self.directory = QFileDialog.getExistingDirectory(self, caption="Select Directory", directory="")
        if self.directory:
            self.video_label.setText(f'Selected Directory: {os.path.basename(self.directory)}')
            self.videos = []

            self.video_dropdown.clear()
            self.video_dropdown.addItem('All videos')

            for dirpath, _, filenames in os.walk(self.directory):
                for file in filenames:
                    if file.lower().endswith(('.mp4', '.mkv')):
                        path = os.path.join(dirpath, file)
                        self.videos.append(path)

            self.video_dropdown.addItems(self.videos)
            self.video_dropdown.setEnabled(True)
            self.on_video_select()


    def on_video_select(self):
        if self.video_dropdown.isEnabled():
            idx = self.video_dropdown.currentIndex()
            if idx == 0 or idx == -1:
                logger.info('Loading all subtitles..')

                self.subtitles = []

                for video in self.videos:
                    subs, success = extract_subs(video)
                    if success:
                        logger.debug(f'Subs loaded for {video}')
                        self.subtitles.append((subs, video))
                    else:
                        logger.error(subs)

                self.load_all_subs()
            else:
                video_str = self.video_dropdown.currentText()
                self.load_video(video=video_str)


    def load_video(self, video=None):
        self.video_file, _ = (video, None) if video else QFileDialog.getOpenFileName(self, caption="Select Video", directory="", filter="Video Files (*.mp4 *.mkv)")
        if self.video_file:
            # Disable dropdown if FileDialog was used
            if not video:
                self.video_dropdown.setEnabled(False)
                self.video_label.setText(f"Selected Video: {os.path.basename(self.video_file)}")

            # Extract subtitles
            subs, success = extract_subs(self.video_file)
            if success:
                logger.success(f'loaded subtitles for {self.video_file}')
                self.subtitles = [(subs, self.video_file)]
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

    def add_header(self, video):
        header = QListWidgetItem(video)
        flags = header.flags()
        flags &= Qt.ItemFlag.ItemIsSelectable
        header.setFlags(flags)
        self.subtitle_results.addItem(header)
        return header


    def search_subtitles(self):
        query = self.subtitle_search_input.text().strip()
        if not self.subtitles:
            self.status_label.setText("Please load subtitles")
            return

        if not query:
            self.load_all_subs()
            return

        self.subtitle_results.clear()
        query_norm = self.normalize_string(query).lower()

        for (subfile, video) in self.subtitles:
            h = self.add_header(video)
            found = any(query_norm in self.normalize_string(sub.text).lower() for sub in subfile)

            if not found:
                self.subtitle_results.takeItem(self.subtitle_results.row(h))
                continue

            for sub in subfile:
                sub_norm = self.normalize_string(sub.text).lower()
                if query_norm in sub_norm:
                    text = f"[{sub.start // 1000}s - {sub.end // 1000}s] {sub.text}"
                    widget = SubtitleListItem(text, source_video=video)
                    self.subtitle_results.addItem(widget)


    def load_all_subs(self):
        self.subtitle_results.clear()
        for (subfile, video) in self.subtitles:
            self.add_header(video)
            for sub in subfile:
                text = f"[{sub.start // 1000}s - {sub.end // 1000}s] {sub.text}"
                widget = SubtitleListItem(text, source_video=video)
                # self.subtitle_results.addItem(result)
                self.subtitle_results.addItem(widget)


    def select_search_result(self, item):
        if isinstance(item, SubtitleListItem):
            text = item.text()
            self.video_file = item.source_video
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
        output_mp4 = "output/output.mp4"
        custom_text = self.custom_text_input.text().strip()
        caption = self.caption_text_input.text().strip()

        if not os.path.exists('output/'):
            os.makedirs('output')

        err, ok = generate_gif(
                start,
                end,
                output_clip,
                output_gif,
                custom_text,
                caption,
                self.video_file,
                self.fps.value(),
                self.square_checkbox.isChecked(),
                self.boomerang_checkbox.isChecked(),
                self.resolution.value(),
                self.selected_font_path,
                self.font_size.value(),
                self.fancy_colors_checkbox.isChecked(),
                self.mp4_copy_checkbox.isChecked(),
                output_mp4
            )

        if ok:
            size_mb = os.path.getsize(output_gif) / (1024 * 1024)
            size_mb = f"{size_mb:.2f}"
            self.status_label.setText(f"GIF generated: {output_gif}, size={size_mb}MB")
            self.preview_gif(output_gif)
            logger.success(f'{output_gif} generated, size={size_mb}MB')
            if self.mp4_copy_checkbox.isChecked():
                size_mb_mp4 = os.path.getsize(output_mp4) / (1024 * 1024)
                size_mb_mp4 = f"{size_mb_mp4:.2f}"
                logger.success(f'{output_mp4} generated, size={size_mb_mp4}MB')
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
