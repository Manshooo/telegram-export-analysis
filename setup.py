
import sys
from setuptools import setup

__version__ = "1.0.0"

setup(
    name="telegram-wordcloud",
    version=__version__,
)

try:
    from semantic_release import setup_hook
    setup_hook(sys.argv)
except ImportError:
    pass
