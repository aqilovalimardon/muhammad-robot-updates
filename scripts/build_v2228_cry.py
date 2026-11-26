"""Build the Rump and Cry commands from the published v2.2.27 Windows runtime."""
import sys

from build_v2223_plush import build


if __name__ == '__main__':
    build(*sys.argv[1:], previous='2.2.27', version='2.2.28', update_voice=True,
          base_sha='cf9959b9801cfae171b5c47d85be8494402e74e889d28ed418e740a9388797c9')
