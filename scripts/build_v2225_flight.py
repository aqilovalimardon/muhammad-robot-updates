"""Ship the new 3D resource pack with the published v2.2.24 Windows host."""
import sys

from build_v2223_plush import build


if __name__ == '__main__':
    build(*sys.argv[1:], previous='2.2.24', version='2.2.25', update_app=False,
          base_sha='014b2ba6f36898f4340258c0c76804a68f3c74b0c928d88690df26f69cf8c408')
