#!/usr/bin/env python3
"""Thin wrapper: l1-graphiti-write lives in ~/.hermes/scripts/ (shared)."""
import pathlib
import runpy
import sys
TARGET = pathlib.Path('/var/home/rainbow/.hermes/scripts/l1-graphiti-write.py')
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name='__main__')
