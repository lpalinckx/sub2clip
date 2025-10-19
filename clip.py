import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QLineEdit, QHBoxLayout, QSpinBox, QWidget, QListWidget, QCheckBox,
    QDoubleSpinBox, QComboBox, QListWidgetItem, QAbstractItemView
)
from PyQt5.QtCore import (Qt)
from PyQt5.QtGui import (QMovie)
from pathlib import Path
from matplotlib import font_manager
import platform
import unicodedata
from subs.subs import (extract_subs, generate_video, generate_sequence)
import argparse
from rangeslider import RangeSlider

from loguru import logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>")

class SubtitleListItem(QListWidgetItem):
    """
    Custom class to show the subtitle in the List widget with the source video stored
    """
    def __init__(self, sub_text, source_video, start_ms, end_ms, sub_id):
        self.sub_text = sub_text
        self.source_video = source_video
        self.start_ms = start_ms
        self.end_ms   = end_ms
        self.start_s = start_ms / 1000
        self.end_s   = end_ms / 1000
        self.sub_id = sub_id

        super().__init__(str(self))
        self.video_basename = os.path.basename(source_video)
        self.setStatusTip(self.video_basename)

    def __str__(self) -> str:
        return f"[{self.start_s}s - {self.end_s}s] {self.sub_text}"

class Sub2Clip(QMainWindow):
    def __init__(self, video=None, directory=None):
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
        self.subtitle_search_input.textChanged.connect(self.search_subtitles)
        self.subtitle_search_button = QPushButton("Search")
        self.subtitle_search_button.clicked.connect(self.search_subtitles)
        self.subtitle_results = QListWidget()
        self.subtitle_results.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.subtitle_results.itemClicked.connect(self.select_search_result)
        subtitle_layout = QHBoxLayout()
        subtitle_layout.addWidget(self.subtitle_search_input)
        subtitle_layout.addWidget(self.subtitle_search_button)
        self.main_layout.addLayout(subtitle_layout)
        self.main_layout.addWidget(self.subtitle_results)

        # Clip Selection
        timing_layout = QVBoxLayout()

        # Range Slider
        self.time_slider = RangeSlider()
        self.time_slider.setRange(0, 1000)
        self.time_slider.rangeChanged.connect(self.on_slider_range_change)

        # Time labels
        time_labels_layout = QHBoxLayout()
        self.start_time_label = QLabel("Start: 0.00s")
        self.end_time_label = QLabel("End: 0.00s")
        time_labels_layout.addWidget(self.start_time_label)
        time_labels_layout.addStretch()
        time_labels_layout.addWidget(self.end_time_label)

        # Time inputs
        time_inputs_layout = QHBoxLayout()
        self.start_time = QDoubleSpinBox()
        self.start_time.setPrefix("Start: ")
        self.start_time.setSuffix(" s")
        self.start_time.setMaximum(9999)
        self.start_time.setSingleStep(0.1)
        self.start_time.setDecimals(2)
        self.start_time.valueChanged.connect(self.on_start_time_change)

        self.end_time = QDoubleSpinBox()
        self.end_time.setPrefix("End: ")
        self.end_time.setSuffix(" s")
        self.end_time.setDecimals(2)
        self.end_time.setSingleStep(0.1)
        self.end_time.setMaximum(9999)
        self.end_time.valueChanged.connect(self.on_end_time_change)

        # Reset button
        self.reset_button = QPushButton("Reset timestamps")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset_timing)
        time_inputs_layout.addWidget(self.start_time)
        time_inputs_layout.addWidget(self.end_time)
        time_inputs_layout.addWidget(self.reset_button)

        timing_layout.addLayout(time_labels_layout)
        timing_layout.addWidget(self.time_slider)
        timing_layout.addLayout(time_inputs_layout)
        self.main_layout.addLayout(timing_layout)

        # Custom Text
        self.custom_text_input = QLineEdit()
        self.custom_text_input.setPlaceholderText("Enter custom text as subtitle (optional)...")
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
        self.square_checkbox = QCheckBox("Square output (crop sides)")

        # Fancy colors (larger GIF size)
        self.fancy_colors_checkbox = QCheckBox("Fancy colors")

        # Create boomerang?
        self.boomerang_checkbox = QCheckBox("Boomerang")

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

        # Generate Button
        self.generate_vid_button = QPushButton("Generate")
        self.generate_vid_button.clicked.connect(self.generate)

        # Format dropdown
        self.select_format = QComboBox()
        self.select_format.addItems(['gif', 'webp'])
        self.select_format.currentTextChanged.connect(self.format_changed)

        self.generate_layout = QHBoxLayout()
        self.generate_layout.addWidget(self.generate_vid_button, stretch=3)
        self.generate_layout.addWidget(self.select_format, stretch=1)
        self.main_layout.addLayout(self.generate_layout)

        # Status
        self.status_label = QLabel("")
        self.main_layout.addWidget(self.status_label)

        # Preview
        self.vid_preview = QLabel("Preview will appear here")
        self.vid_preview.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.vid_preview)

        # Set Layout
        container = QWidget()
        container.setLayout(self.main_layout)
        self.setCentralWidget(container)

        # Variables
        self.video_file = None
        self.subtitle_file = None
        self.subtitles = []
        self.subtitle_list_items = []
        self.PADDING = 10 # Time in seconds to pad the original timing on each side for the slider

        if platform.system() == 'Windows':
            self.selected_font_path = Path("C:/Windows/Fonts/arial.ttf")
        else: self.selected_font_path = ''

        if video:
            logger.info(f'Loading video path {video}')
            self.load_video(video)
        elif directory:
            logger.info(f'Loading directory {directory}')
            self.load_directory(directory=directory)


    def load_directory(self, directory=None):
        self.directory = directory if directory else QFileDialog.getExistingDirectory(self, caption="Select Directory", directory="")
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

            self.videos.sort()
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
        """Load a video file and update the time slider range"""

        # If video is None or False, open file dialog
        if video is None or video is False:
            video_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.mkv)")
            if not video_path:  # User cancelled the dialog
                return
            video = str(video_path)  # Ensure it's a string


        if not isinstance(video, (str, bytes, os.PathLike)):
            logger.error(f"Invalid video path type: {type(video)}, value: {video}")
            self.status_label.setText("Invalid video path")
            return

        # Convert to string if it's a PathLike object
        video = str(video)

        # Check if file exists
        if not os.path.exists(video):
            logger.error(f"Video file not found: {video}")
            self.status_label.setText("Video file not found")
            return

        self.video_file = video
        self.video_label.setText(f"Selected Video: {os.path.basename(video)}")

        # Disable dropdown if FileDialog was used
        if video is None:
            self.video_dropdown.setEnabled(False)

        # Extract subtitles
        subs, success = extract_subs(self.video_file)
        if success:
            logger.success(f'Loaded subtitles for {self.video_file}')
            self.subtitles = [(subs, self.video_file)]
            self.status_label.setText("Subtitles loaded successfully!")

            # Set up time slider with 10 second range and padding
            self.time_slider.setRange(0, 1000)  # 1000 steps for precision
            self.time_slider.setValues(0, 1000)  # Set full range initially

            # Set initial times with padding
            self.start_time.setValue(0)  # 1 second padding at start
            self.end_time.setValue(0)    # 1 second padding at end
            self.start_time_label.setText("")
            self.end_time_label.setText("")

            self.time_slider.setEnabled(False)

            self.load_all_subs()
        else:
            logger.error(f"Failed to extract subtitles: {subs}")
            self.status_label.setText("No subtitles found.")

    def format_changed(self):
        if self.select_format.currentText() == 'gif':
            self.fancy_colors_checkbox.setEnabled(True)
        else: self.fancy_colors_checkbox.setEnabled(False)

    def on_font_select(self):
        font_str = self.font_dropdown.currentText()
        font_path = self.font_dict[font_str]

        self.font_label.setText(f'Font: {font_str}')
        self.selected_font_path = font_path

    def normalize_string(self, s):
        return ''.join(
            c for c in unicodedata.normalize('NFD', s.replace('\\N', ' '))
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

            for subItem in self.subtitle_list_items:
                if subItem.source_video != video:
                    continue

                sub_norm = self.normalize_string(subItem.sub_text).lower()
                if query_norm in sub_norm:
                    widget = SubtitleListItem(
                        sub_text=subItem.sub_text,
                        source_video=subItem.source_video,
                        start_ms=subItem.start_ms,
                        end_ms=subItem.end_ms,
                        sub_id=subItem.sub_id
                    )
                    self.subtitle_results.addItem(widget)


    def load_all_subs(self):
        self.subtitle_results.clear()
        self.subtitle_list_items = []
        for (subfile, video) in self.subtitles:
            self.add_header(video)
            for idx, sub in enumerate(subfile):
                widget = SubtitleListItem(
                    sub_text=sub.text,
                    source_video=video,
                    start_ms=sub.start,
                    end_ms=sub.end,
                    sub_id=idx
                )
                self.subtitle_list_items.append(widget)
                self.subtitle_results.addItem(widget)


    def select_search_result(self, item):
        if isinstance(item, SubtitleListItem):
            self.time_slider.setEnabled(True)

            selected_items = self.subtitle_results.selectedItems()
            selected_items.sort(key=lambda i: i.start_ms)

            self.video_file = item.source_video

            # Store original subtitle times
            self.original_start = float(selected_items[0].start_s)
            self.original_end = float(selected_items[-1].end_s)

            # Set initial times to original subtitle times
            self.start_time.setValue(self.original_start)
            self.end_time.setValue(self.original_end)

            # Update slider range based on original times
            self.time_slider.setRange(0, 1000)  # 1000 steps for precision

            # Calculate slider positions for original timing
            start_pos = self._time_to_slider(self.original_start)
            end_pos = self._time_to_slider(self.original_end)

            # Set initial slider positions
            self.time_slider.setValues(start_pos, end_pos)

            # Set original timing indicators
            self.time_slider.setOriginalTimes(start_pos, end_pos)

            # Update labels
            self.start_time_label.setText(f"Start: {self.original_start:.2f}s")
            self.end_time_label.setText(f"End: {self.original_end:.2f}s")

            self.custom_text_input.setText(item.sub_text)

            # Enable reset button
            self.reset_button.setEnabled(True)

    def reset_timing(self):
        """Reset the timing to the original subtitle times"""
        if hasattr(self, 'original_start') and hasattr(self, 'original_end'):
            self.start_time.setValue(self.original_start)
            self.end_time.setValue(self.original_end)
            self.time_slider.resetToOriginal()

    def generate(self):
        if not os.path.exists('output/'):
            os.makedirs('output')

        items = self.subtitle_results.selectedItems()
        items.sort(key=lambda i: i.start_ms)

        if len(items) > 1:
            if any(curr.sub_id != prev.sub_id + 1 for prev, curr in zip(items, items[1:])):
                s = 'Illegal sequence of subtitles: Selected subtitles must be sequential'
                self.status_label.setText(s)

                logger.error(s)
                return

            video_settings = [
                {
                    'start_time': sub.start_s if (idx != 0) else self.start_time.value(),
                    'end_time': sub.end_s if (idx != len(items)-1) else self.end_time.value(),
                    'custom_text': sub.sub_text,
                    'font': self.selected_font_path,
                    'font_size': self.font_size.value()
                } for idx, sub in enumerate(items)
            ]

            output_vid = f'output/output.{self.select_format.currentText()}'
            output_mp4 = 'output/mp4_concat.mp4'

            err, ok = generate_sequence(
                source_video=self.video_file,
                output_format=self.select_format.currentText(),
                video_settings=video_settings,
                output_path=output_vid,
                output_mp4=output_mp4,
                caption=self.caption_text_input.text().strip(),
                fps=self.fps.value(),
                crop=self.square_checkbox.isChecked(),
                resolution=self.resolution.value(),
                fancy_colors=self.fancy_colors_checkbox.isChecked()
            )

            if ok:
                size_mb = os.path.getsize(output_vid) / (1024 * 1024)
                size_mb = f"{size_mb:.2f}"
                self.status_label.setText(f"'{output_vid}' generated, size={size_mb}MB")
                self.preview_vid(output_vid)
                logger.success(f'{output_vid} generated, size={size_mb}MB')
            else:
                logger.error(err)

        else:
            self.generate_vid()


    def generate_vid(self):
        if not self.video_file:
            self.status_label.setText("Please load a video first.")
            return

        start = self.start_time.value()
        end = self.end_time.value()
        if start >= end:
            self.status_label.setText("Invalid start and end times.")
            return

        output_clip = "output/clip.mp4"
        output_vid = f"output/output.{self.select_format.currentText()}"
        output_mp4 = "output/output.mp4"
        custom_text = self.custom_text_input.text().strip()
        caption = self.caption_text_input.text().strip()

        if not os.path.exists('output/'):
            os.makedirs('output')

        err, ok = generate_video(
                start,
                end,
                output_clip,
                output_vid,
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
                self.select_format.currentText(),
                self.mp4_copy_checkbox.isChecked(),
                output_mp4
            )

        if ok:
            size_mb = os.path.getsize(output_vid) / (1024 * 1024)
            size_mb = f"{size_mb:.2f}"
            self.status_label.setText(f"{output_vid} generated, size={size_mb}MB")
            self.preview_vid(output_vid)
            logger.success(f'{output_vid} generated, size={size_mb}MB')
            if self.mp4_copy_checkbox.isChecked():
                size_mb_mp4 = os.path.getsize(output_mp4) / (1024 * 1024)
                size_mb_mp4 = f"{size_mb_mp4:.2f}"
                logger.success(f'{output_mp4} generated, size={size_mb_mp4}MB')
        else:
            self.status_label.setText(f"Something went wrong during generation")
            logger.error(err)

    def preview_vid(self, vid_path):
        self.vid_movie = QMovie(vid_path)
        self.vid_preview.setMovie(self.vid_movie)
        self.vid_movie.start()

    def close(self):
        logger.success("closing...")

    def _slider_to_time(self, slider_value):
        step = 1000 / (self.original_end - self.original_start + 2 * self.PADDING)
        slider_zero = self.original_start - self.PADDING
        return (slider_value / step) + slider_zero

    def _time_to_slider(self, time):
        step = 1000 / (self.original_end - self.original_start + 2 * self.PADDING)
        slider_zero = self.original_start - self.PADDING
        return (time - slider_zero) * step

    def on_slider_range_change(self, start, end):
        """Update time labels and spinboxes when slider range changes"""
        if not hasattr(self, 'original_start') or not hasattr(self, 'original_end'):
            self.status_label.setText("Please select a subtitle first")
            return

        # Convert slider values to actual times
        start_time = self._slider_to_time(start)
        end_time = self._slider_to_time(end)

        # Ensure times don't go negative
        start_time = max(0, start_time)
        end_time = max(0, end_time)

        self.start_time.setValue(start_time)
        self.start_time_label.setText(f"Start: {start_time:.2f}s")
        self.end_time.setValue(end_time)
        self.end_time_label.setText(f"End: {end_time:.2f}s")

    def on_start_time_change(self, value):
        """Update slider and labels when start time changes"""
        if not hasattr(self, 'original_start') or not hasattr(self, 'original_end'):
            self.status_label.setText("Please select a subtitle first")
            return

        # Convert time to slider value
        slider_value = self._time_to_slider(value)

        # Ensure slider value stays within bounds
        slider_value = max(0, min(1000, slider_value))

        current_end = self.time_slider._end
        self.time_slider.setValues(slider_value, current_end)
        self.start_time_label.setText(f"Start: {value:.2f}s")

    def on_end_time_change(self, value):
        """Update slider and labels when end time changes"""
        if not hasattr(self, 'original_start') or not hasattr(self, 'original_end'):
            self.status_label.setText("Please select a subtitle first")
            return

        # Convert time to slider value
        slider_value = self._time_to_slider(value)

        # Ensure slider value stays within bounds
        slider_value = max(0, min(1000, slider_value))

        current_start = self.time_slider._start
        self.time_slider.setValues(current_start, slider_value)
        self.end_time_label.setText(f"End: {value:.2f}s")

# Run the app
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog = 'Sub2Clip'
    )
    parser.add_argument('--video', help="path to a video")
    parser.add_argument('--directory', help="path to a directory containing videos")
    args = parser.parse_args()

    directory_path = args.directory if args.directory else None
    video_path     = args.video  if args.video  else None

    app = QApplication(sys.argv)
    window = Sub2Clip(video=video_path, directory=directory_path)
    window.show()

    app.aboutToQuit.connect(window.close)

    sys.exit(app.exec_())
