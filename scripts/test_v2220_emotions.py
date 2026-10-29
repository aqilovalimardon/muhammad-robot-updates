#!/usr/bin/env python3
"""Run the deployed updater and all host regressions on the v2.2.20 package."""
import sys
from test_v2219_plush import main

if __name__ == '__main__':
    main(*sys.argv[1:], expected_version='2.2.20',
         expected_changed={'app/robot_core.py', 'app/visual3d/MuhammadRobot3D.pck'})
