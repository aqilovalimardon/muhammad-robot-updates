"""Build the whistling dance from the published v2.2.29 Windows runtime."""
import sys

from build_v2223_plush import build


if __name__ == '__main__':
    build(*sys.argv[1:], previous='2.2.29', version='2.2.30', update_voice=True,
          base_sha='694c8d6c9745eb650edd9f1a3d779137e6de1b04c159f526057dc32074894ae1')
