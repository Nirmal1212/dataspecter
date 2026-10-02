"""Lets `python -m dataspecter` run the command, for when the installed script cannot be used."""

import sys

from dataspecter.cli import main

sys.exit(main())
