
import json
import re
from typing import Literal, List, Optional
from collections import Counter


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
