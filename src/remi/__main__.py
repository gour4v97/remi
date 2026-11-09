"""Package entry point allowing python -m remi execution."""
import sys
from remi.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
