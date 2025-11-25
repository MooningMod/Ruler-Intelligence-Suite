import sys
import argparse
from PyQt5.QtWidgets import QApplication
from overlay_ins_menu import OverlayINS

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-unit", default=None, help="Path to DEFAULT.UNIT")
    parser.add_argument("--default-ttrx", default=None, help="Path to DEFAULT.TTRX")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    # Passiamo entrambi i path all'overlay
    overlay = OverlayINS(
        default_unit_path=args.default_unit,
        default_ttrx_path=args.default_ttrx
    )
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()