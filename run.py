
import argparse
import sys
from dataclasses import dataclass
from typing import Optional, Dict
import numpy as np
import imageio
from wordcloud import WordCloud
from tools import (
    Conversation,
    get_chat_list,
    find_chat_by_name,
    ShapeType,
)

# сделать выбор цвета фона


@dataclass
class WCConfig:
    """Word Cloud configuration"""
    max_font_size: int = 250
    width: int = 1920
    height: int = 1080
    max_words: int = 1000
    background_color: str = 'black'
    mode: str = 'RGB'
    font_path: Optional[str] = None
    prefer_horizontal: float = 0.9
    relative_scaling: float = 0.5


def create_mask(shape: ShapeType, width: int, height: int) -> Optional[np.ndarray]:
    """Create mask array for word cloud"""
    if shape == "circle":
        y, x = np.ogrid[:height, :width]
        center_x, center_y = width//2, height//2
        radius = min(width, height) // 2 - 10
        mask = (x - center_x)**2 + (y - center_y)**2 > radius**2
        return (255 * mask.astype(int))
    return None


def calculate_frequencies(selected_conv: Conversation, other_chats: list) -> Dict[str, float]:
    """Calculate word frequencies with comparison logic"""
    total_words = 0
    global_counts = dict()

    # Process other chats
    for chat in other_chats:
        conv = Conversation(chat)
        words = conv.get_word_list()
        total_words += len(words)
        for word, count in conv.count_words().items():
            global_counts[word] = global_counts.get(word, 0) + count

    # Calculate probabilities
    global_probs = {word: count/total_words for word,
                    count in global_counts.items()} if total_words else {}

    # Process selected chat
    selected_counts = selected_conv.count_words()
    selected_total = len(selected_conv.get_word_list())

    if not other_chats:
        return {word: count/selected_total for word, count in selected_counts.items()}

    # Calculate frequency ratios
    all_words = set(selected_counts) | set(global_probs)
    return {
        word: (selected_counts.get(word, 0)/selected_total) /
        (global_probs.get(word, 1e-10))
        for word in all_words
    }


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate comparative word clouds from Telegram chats")

    parser.add_argument('filename', help='Path to JSON export file')
    parser.add_argument('chat_name', nargs='?', default=None,
                        help='Name of chat to analyze (optional for single chat files)')

    shape_group = parser.add_argument_group('Shape options')
    shape_group.add_argument('-s', '--shape', choices=['circle', 'rect'],
                             help='Cloud shape: circle or rectangle')
    shape_group.add_argument('--size', nargs=2, type=int, metavar=('WIDTH', 'HEIGHT'),
                             help='Image dimensions in pixels')
    shape_group.add_argument('--width', type=int, help='Image width')
    shape_group.add_argument('--height', type=int, help='Image height')

    args = parser.parse_args()

    # Validate size arguments
    if (args.width or args.height) and args.size:
        parser.error("Use either --size or --width/--height")
    if (args.width and not args.height) or (args.height and not args.width):
        parser.error("Must specify both width and height")

    return args


def main():
    """Main process"""
    args = parse_args()

    # Determine image size
    if args.size:
        width, height = args.size
    elif args.width and args.height:
        width, height = args.width, args.height
    else:
        default_config = WCConfig()
        width, height = default_config.width, default_config.height

    # Load and validate chats
    chats = get_chat_list(args.filename)
    if not chats:
        sys.exit("No chats found in file")

    # Select target chat
    if args.chat_name:
        selected_chat = find_chat_by_name(args.chat_name, chats)
        if not selected_chat:
            sys.exit(f"Chat '{args.chat_name}' not found")
    else:
        if len(chats) > 1:
            sys.exit("Multiple chats found - please specify chat name")
        selected_chat = chats[0]

    # Prepare data
    other_chats = [chat for chat in chats if chat != selected_chat]
    selected_conv = Conversation(selected_chat)

    # Generate word frequencies
    frequencies = calculate_frequencies(selected_conv, other_chats)

    # Configure word cloud
    config = WCConfig(width=width, height=height)
    mask = create_mask(args.shape or 'rect', width, height)

    wc = WordCloud(
        **vars(config),
        mask=mask
    ).generate_from_frequencies(frequencies)

    # Save result
    output_file = f"{selected_chat['name']}-diff.png"
    imageio.imwrite(output_file, wc)
    print(f"Word cloud saved to {output_file}")


if __name__ == "__main__":
    main()
