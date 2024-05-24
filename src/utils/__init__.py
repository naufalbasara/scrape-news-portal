import numpy as np, pandas as pd, json, os, re

def get_rootdir() -> str:
    cwd = os.path.abspath(os.getcwd())
    end = re.search(r'scrape-news-portal', cwd).end()
    rootdir = cwd[:end]

    return rootdir