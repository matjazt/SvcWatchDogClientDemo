import sys
import os

# add the parent directory to the system path, so we can import the modules the same way as in the main program
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
