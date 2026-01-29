import sys

import pytest

# Prevent pytest from collecting this file
__test__ = False


def run_single_test(test_path):
    """
    Utility to run a single test.
    """
    pytest.main([test_path, "-v"])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single_test(sys.argv[1])
    else:
        print("Usage: python debug_single_test.py <path_to_test>")
