"""Permite correr `python -m lisart` sin instalar el comando."""

import sys

from lisart.cli import main

if __name__ == "__main__":
    sys.exit(main())
