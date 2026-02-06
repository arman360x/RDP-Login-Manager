import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import RDPManagerApp


def main():
    app = RDPManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
