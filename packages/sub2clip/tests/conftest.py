import os
import sys
from pathlib import Path

# Add the package root to the Python path
package_root = Path(__file__).parent.joinpath('src')
sys.path.insert(0, str(package_root))