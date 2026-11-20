"""Package the four voice actions with the deployed 3D-only Windows runtime."""
import sys

from build_v2223_plush import build


if __name__ == '__main__':
    build(*sys.argv[1:], previous='2.2.23', version='2.2.24', update_voice=True,
          base_sha='639e6713fc2f831c9c17d5c54b28e3145d3f7e599d3513917a14a172de55af84')
