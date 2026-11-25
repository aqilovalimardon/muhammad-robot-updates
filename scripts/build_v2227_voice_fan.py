"""Build the offline voice and wide flight-trail update from the published v2.2.26 ZIP."""
import sys

from build_v2223_plush import build


if __name__ == '__main__':
    build(*sys.argv[1:], previous='2.2.26', version='2.2.27', update_voice=True,
          base_sha='b3bbe941112006d2f13be7e662ef2d7932cdc20e63ec632dfbda2549ed2bdf45')
