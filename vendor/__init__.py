import os
import sys

vendor_path = os.path.abspath(os.path.dirname(__file__))

curtsies_path = os.path.join(vendor_path, "curtsies")

sys.path.insert(0, curtsies_path)
