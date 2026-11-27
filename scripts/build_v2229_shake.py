"""Build Jump and mouse-shake crying from the published v2.2.28 Windows runtime."""
import sys

from build_v2223_plush import build


if __name__ == '__main__':
    build(*sys.argv[1:], previous='2.2.28', version='2.2.29', update_voice=True,
          base_sha='3fbd860b83f9d15978325e30d32b78f81941d540de5955fac9eef9f7aeb72915')
