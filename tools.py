
import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Literal, Optional

import matplotlib.colors as mcolors
import numpy as np


class Conversation:
    PUNCTUATION = r""",!\.…/"'\(\)\*\?=–;:^—~«»"""
    CLEAN_REGEX = re.compile(f"[{PUNCTUATION}]")

    def __init__(self, chat: dict):
        self.messages = chat['messages']
        self.name = chat['name']
        self._word_filter = lambda msg: True

    def get_word_list(self) -> List[str]:
        words = []
        for msg in self.messages:
            if not self._word_filter(msg):
                continue

            text = msg.get('text', '')
            if not isinstance(text, str):
                continue

            cleaned = self.CLEAN_REGEX.sub(' ', text.lower())
            words.extend(filter(None, re.split(r'\s+', cleaned.strip())))
        return words

    def count_words(self) -> Counter:
        return Counter(self.get_word_list())


ShapeType = Literal["circle", "rect"]


def get_chat_list(filename: str) -> List[dict]:
    """Load chats from JSON file"""
    with open(filename, encoding='utf-8') as f:
        data = json.load(f)

    if 'chats' in data:
        return data['chats']['list']
    return [data]


def find_chat_by_name(name: str, chats: list) -> Optional[dict]:
    """Find chat by name (case sensitive)"""
    return next((c for c in chats if c.get('name') == name), None)


def get_contrast_color(background_color: str) -> str:
    """Get black or white depending on background luminance"""
    try:
        rgb = mcolors.to_rgb(background_color)
    except ValueError:
        rgb = (0, 0, 0)  # Fallback to black on error

    # Calculate luminance (per ITU-R BT.709)
    luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return "#000000" if luminance > 0.5 else "#ffffff"


def create_mask(shape: ShapeType, width: int, height: int) -> Optional[np.ndarray]:
    """Create mask array for word cloud"""
    if shape == "circle":
        y, x = np.ogrid[:height, :width]
        center_x, center_y = width//2, height//2
        radius = min(width, height) // 2 - 10
        mask = (x - center_x)**2 + (y - center_y)**2 > radius**2
        return 255 * mask.astype(int)
    return None


def calculate_frequencies(selected_conv: Conversation,
                          other_chats: list,
                          excluded_words: set[str]) -> Dict[str, float]:
    """Calculate word frequencies with comparison logic, excluding specific words"""
    total_words = 0
    global_counts = {}

    # Process other chats with filtering
    for chat in other_chats:
        conv = Conversation(chat)
        word_counts = conv.count_words()

        # Filter excluded words
        filtered_counts = {
            word: count
            for word, count in word_counts.items()
            if word not in excluded_words
        }

        total_words += sum(filtered_counts.values())
        for word, count in filtered_counts.items():
            global_counts[word] = global_counts.get(word, 0) + count

    # Calculate probabilities
    global_probs = {}
    if total_words:
        global_probs = {word: count / total_words for word,
                        count in global_counts.items()}

    # Process selected chat with filtering
    selected_counts_raw = selected_conv.count_words()
    selected_counts = {
        word: count
        for word, count in selected_counts_raw.items()
        if word not in excluded_words
    }
    # Prevent division by zero
    selected_total = sum(selected_counts.values()) or 1

    if not other_chats:
        return {word: count / selected_total for word, count in selected_counts.items()}

    # Calculate frequency ratios
    all_words = set(selected_counts) | set(global_probs)
    return {
        word: (selected_counts.get(word, 0) / selected_total) /
        (global_probs.get(word, 1e-10))
        for word in all_words
    }


def generate_unique_filename(path: str) -> str:
    """Generates unique filename with suffixes (1), (2) and etc."""
    counter = 1
    original_path = Path(path)
    stem = original_path.stem
    suffix = original_path.suffix

    while original_path.exists():
        new_name = f"{stem}({counter}){suffix}"
        original_path = original_path.with_name(new_name)
        counter += 1

    return str(original_path)


class ColorConfig:
    """Color config from file or uses default"""
    DEFAULT_CONFIG = {
        "color_palettes": {
            "light_background": ["#0A0A0A", "#2D4261", "#4A1D32", "#1D4A3F", "#3D2B56"],
            "dark_background": ["#FAFAFA", "#D6E4F0", "#F5D6E4", "#D6F5E4", "#E4D6F5"]
        }
    }

    def __init__(self, config_path: str = None):
        self.config = self.DEFAULT_CONFIG
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, encoding='utf-8') as f:
                    self.config = json.load(f)
                self._validate()
            except (FileNotFoundError, IOError) as e:
                print(f"Error loading config: {e}. Using default colors")

    def _validate(self):
        required = ["light_background", "dark_background"]
        if not all(key in self.config["color_palettes"] for key in required):
            raise ValueError("Invalid color palettes in config")


class ContrastColorFunc:
    """Color func for contrast text colors with variations"""

    def __init__(self, bg_color: str, config: ColorConfig):
        self.bg_luminance = self.calculate_luminance(bg_color)
        self.palette_type = "light_background" if self.bg_luminance > 0.5 else "dark_background"
        self.colors = config.config["color_palettes"][self.palette_type]

    @staticmethod
    def calculate_luminance(color: str) -> float:
        """Calculate lumanance value of given color 0..1"""
        try:
            rgb = mcolors.to_rgb(color)
        except ValueError:
            return 0
        return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

    def generate_palette(self):
        """Generate contrasting color palette"""
        if self.bg_luminance > 0.5:
            # Dark colors for light background
            return [
                '#0A0A0A', '#2D4261', '#4A1D32',
                '#1D4A3F', '#3D2B56', '#2B5647'
            ]
        else:
            # Light colors for dark background
            return [
                '#FAFAFA', '#D6E4F0', '#F5D6E4',
                '#D6F5E4', '#E4D6F5', '#E4F5D6'
            ]

    def __call__(self, word, **kwargs):
        """Random color from palette for each word"""
        return np.random.choice(self.colors)
