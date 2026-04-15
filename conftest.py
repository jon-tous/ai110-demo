import sys
import pathlib

# Add project root to sys.path so `from src.X import ...` works in tests
sys.path.insert(0, str(pathlib.Path(__file__).parent))
