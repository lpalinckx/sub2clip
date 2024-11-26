import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QLineEdit, QHBoxLayout, QSpinBox, QWidget, QListWidget, QCheckBox,
    QDoubleSpinBox, QComboBox
)
from PyQt5.QtCore import (Qt)
from PyQt5.QtGui import (QMovie)
import subprocess
import pysubs2
from pathlib import Path
from matplotlib import font_manager
import platform

from loguru import logger 
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class GifCreatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GIF Creator")
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
        self.font_label  = QLabel("Font: Arial (default)")
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


    def load_video(self):
        self.video_file, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Video Files (*.mp4 *.mkv)")
        if self.video_file:
            self.video_label.setText(f"Selected Video: {os.path.basename(self.video_file)}")
            # Extract subtitles
            self.subtitle_file = os.path.splitext(self.video_file)[0] + ".srt"
            subprocess.run(["ffmpeg", "-i", self.video_file, "-map", "0:s:0", self.subtitle_file, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(self.subtitle_file):
                self.subtitles = pysubs2.load(self.subtitle_file)
                self.status_label.setText("Subtitles loaded successfully!")
                self.load_all_subs()
            else:
                self.status_label.setText("No subtitles found.")
    

    def on_font_select(self):
        font_str = self.font_dropdown.currentText()
        font_path = self.font_dict[font_str]

        self.font_label.setText(f'Font: {font_str}')
        self.selected_font_path = font_path
    

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
            if query.lower() in sub.text.lower():
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

        duration = end - start

        if not os.path.exists('output/'):
            os.makedirs('output')

        # Clip the video
        subprocess.run([
            "ffmpeg", 
            "-ss", str(start), 
            "-i", self.video_file, 
            "-t", str(duration), 
            "-c:v", "copy", 
            "-c:a", "copy", 
            output_clip, 
            "-y"], 
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        

        # Base command 
        ffmpeg_vf = (
            f"fps={self.fps.value()},"
            f"{'crop=in_h:in_h,' if self.square_checkbox.isChecked() else ''}"
            f"scale={self.resolution.value()}:-1:flags=lanczos,"
            f"split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        )

        if custom_text: 
            lines = custom_text.split("\\N")[::-1]

            for i, line in enumerate(lines, start=1):
                # Writing the line to a file helps circumvent ffmpeg's weird escaping rules ¯\_(ツ)_/¯
                line_filename = f'output/line-{i}.txt'
                with open(line_filename, 'w', encoding='utf-8') as file:
                    file.write(line)

                font_path = self.selected_font_path.as_posix().replace(':', r'\:')

                # Add the subtitle text to the video 
                ffmpeg_vf += (
                    f",drawtext=textfile='{line_filename}':"
                    f"fontfile='{font_path}':"
                    f"fontcolor=white:"
                    f"fontsize={self.font_size.value()}:"
                    f"x=(w-text_w)/2:"
                    f"y=(h-{i}*line_h)"
                )

            logger.debug(ffmpeg_vf)

        # Generate GIF
        command = ["ffmpeg", "-y", "-i", output_clip, "-vf", ffmpeg_vf, output_gif]
        try:
            logger.info(f'Full command = "{" ".join(command)}"')
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e: 
            logger.error(e)

        try:
            size_mb = os.path.getsize(output_gif) / (1024 * 1024)  
            size_mb = f"{size_mb:.2f}" 
            self.status_label.setText(f"GIF generated: {output_gif}, size={size_mb}MB")
            self.preview_gif(output_gif)       
            logger.success(f'{output_gif} generated, size={size_mb}MB')

            # Cleanup textfiles
            for txtfile in list(Path('output/').glob('line-*.txt')):
                txtfile.unlink()

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            self.status_label.setText(f"Something went wrong creating the GIF")
            size_mb = -1

    def preview_gif(self, gif_path):
        self.gif_movie = QMovie(gif_path)
        self.gif_preview.setMovie(self.gif_movie)
        self.gif_movie.start()


    def cleanup_tmp_files(self):
        if os.path.exists(self.subtitle_file):
            os.remove(self.subtitle_file)


# Run the app
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GifCreatorApp()
    window.show()

    app.aboutToQuit.connect(window.cleanup_tmp_files)

    sys.exit(app.exec_())
