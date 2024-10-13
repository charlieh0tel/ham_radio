#!/usr/bin/python3

import pickle
import sys

def main(argv):
    with open("thru_calibration.pkl", "rb") as f:
        print(pickle.load(f))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
        
