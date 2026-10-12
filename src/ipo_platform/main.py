"""
Main entry point module for the Indian IPO Platform package.
Delegates directly to the operational CLI main function.
"""

import sys
from ipo_platform.cli import main

if __name__ == "__main__":
    sys.exit(main())
