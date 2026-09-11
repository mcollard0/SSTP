"""Main entry point for Stuart Saves the Pomodoro (SSTP)."""

import sys
from sstp.app import main

if __name__ == "__main__":
    sys.exit(main() or 0)
