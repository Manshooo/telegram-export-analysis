
import argparse
import os
import sys
from dataclasses import dataclass
from typing import Optional
import imageio
from wordcloud import WordCloud
from tools import (
    ColorConfig,
    ContrastColorFunc,
    Conversation,
    calculate_frequencies,
    create_mask,
    generate_unique_filename,
    get_chat_list,
    find_chat_by_name,
)


@dataclass
class WCConfig:
    """Word Cloud configuration"""
    max_font_size: int = 250
    width: int = 500
    height: int = 500
    max_words: int = 1000
    background_color: str = 'black'
    mode: str = 'RGB'
    font_path: Optional[str] = None
    prefer_horizontal: float = 0.9
    relative_scaling: float = 0.5


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate comparative word clouds from Telegram chats")

    parser.add_argument('filename', help='Path to JSON export file')
    parser.add_argument('chat_name', nargs='?', default=None,
                        help='Name of chat to analyze (optional for single chat files)')
    parser.add_argument('--config', type=str, default='.wc',
                        help='Path to color config file')

    shape_group = parser.add_argument_group('Shape options')
    shape_group.add_argument('-s', '--shape', choices=['circle', 'rect'],
                             help='Cloud shape: circle or rectangle')
    shape_group.add_argument('--size', nargs=2, type=int, metavar=('WIDTH', 'HEIGHT'),
                             help='Image dimensions in pixels',
                             default=[500, 500])
    shape_group.add_argument('--width', type=int, help='Image width')
    shape_group.add_argument('--height', type=int, help='Image height')

    style_group = parser.add_argument_group('Style options')
    style_group.add_argument('--bg-color', type=str, default='black',
                             metavar='COLOR',
                             help='Background color (name or hex code)')
    style_group.add_argument('--monochrome', action='store_true',
                             help='Use black/white text instead of colored')

    output_group = parser.add_argument_group('Output options')
    output_group.add_argument('-o', '--output', type=str,
                              metavar='OUTPUT',
                              help='Custom output file path')
    output_group.add_argument('--no-overwrite', action='store_false',
                              dest='overwrite', default=True,
                              help='Disable file overwriting')
    output_group.add_argument('--exclude', type=lambda s: set(s.lower().split(',')),
                              default=set(['а', 'в', 'н', 'и', 'э', 'я', 'у',
                                           'вы', 'не', 'ну', 'мы', 'ты', 'он',
                                           'по',
                                           'что', 'это', 'нет', 'так', 'она',
                                           'вот', 'мне', 'всё', 'ещё', 'или',
                                           'тут', 'там',
                                           ]),
                              metavar='WORDS',
                              help='Comma-separated words to exclude (case-insensitive)')

    args = parser.parse_args()

    # Validation
    if (args.width or args.height) and args.size:
        parser.error("Use either --size or --width/--height")
    if (args.width and not args.height) or (args.height and not args.width):
        parser.error("Must specify both width and height")

    return args


def main():
    """Main process"""
    args = parse_args()

    color_config = ColorConfig(args.config)

    # Определение размера изображения
    if args.size:
        width, height = args.size
    elif args.width and args.height:
        width, height = args.width, args.height
    else:
        default_config = WCConfig()
        width, height = default_config.width, default_config.height

    # Загрузка и валидация чатов
    chats = get_chat_list(args.filename)
    if not chats:
        sys.exit("No chats found in file")

    # Выбор целевого чата
    if args.chat_name:
        selected_chat = find_chat_by_name(args.chat_name, chats)
        if not selected_chat:
            sys.exit(f"Chat '{args.chat_name}' not found")
    else:
        if len(chats) > 1:
            sys.exit("Multiple chats found - please specify chat name")
        selected_chat = chats[0]

    # Подготовка данных
    other_chats = [chat for chat in chats if chat != selected_chat]
    selected_conv = Conversation(selected_chat)

    # Генерация частот слов
    frequencies = calculate_frequencies(
        selected_conv,
        other_chats,
        excluded_words=args.exclude
    )

    # Настройка облака слов
    config = WCConfig(
        width=width,
        height=height,
        background_color=args.bg_color
    )
    mask = create_mask(args.shape or 'rect', width, height)

    # Автоматический подбор цвета текста
    if args.monochrome:
        color_func = ContrastColorFunc(args.bg_color, color_config)

        def mono_func(*_args, **_kwargs):
            return "#000000" if color_func.bg_luminance > 0.5 else "#ffffff"
        color_func.__call__ = mono_func
    else:
        color_func = ContrastColorFunc(args.bg_color, color_config)

    # Генерация изображения
    wc = WordCloud(
        **vars(config),
        mask=mask,
        color_func=color_func
    ).generate_from_frequencies(frequencies)

    # Сохранение результата
    output_file = args.output if args.output else f"{selected_chat['name']}-wc.png"
    output_path = os.path.abspath(output_file)

    if not args.overwrite:
        output_path = generate_unique_filename(output_path)

    imageio.imwrite(output_path, wc)
    print(f"Word cloud saved to: {output_path}")


if __name__ == "__main__":
    main()
