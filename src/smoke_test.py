import sys
import requests
import pandas as pd

def main():
    print("Python:", sys.version.split()[0])
    print("requests:", requests.__version__)
    print("pandas:", pd.__version__)
    print("OK: environment ready")

if __name__ == "__main__":
    main()
