"""Package the new greeting and flight trail with the published v2.2.25 host."""
import sys

from build_v2223_plush import build


if __name__ == '__main__':
    build(*sys.argv[1:], previous='2.2.25', version='2.2.26', update_app=False,
          base_sha='7215c047ea6edd0bfa9aaa9b22c80c80d6e96c1d6ed17043f4f51b3a4ecc5bf2')
