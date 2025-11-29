import sys
import argparse
from PyQt5.QtWidgets import QApplication
from overlay_ins_menu import OverlayINS

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-unit", default=None, help="Path to DEFAULT.UNIT")
    parser.add_argument("--default-ttrx", default=None, help="Path to DEFAULT.TTRX")
    parser.add_argument("--default-spotting", default=None, help="Path to Spotting.csv")
    parser.add_argument("--range-database", default=None, help="Path to unit_rangestats_database.csv")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    # Pass all four paths to overlay
    overlay = OverlayINS(
        default_unit_path=args.default_unit,
        default_ttrx_path=args.default_ttrx,
        default_spotting_path=args.default_spotting,
        range_database_path=args.range_database
    )
    sys.exit(app.exec_())
    
def closeEvent(self, event):
    print("[Overlay] Closing overlay window.")
    QApplication.quit()
    event.accept()


if __name__ == "__main__":
    main()