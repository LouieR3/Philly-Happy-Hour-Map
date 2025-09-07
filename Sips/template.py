import pandas as pd
from yelpapi import YelpAPI
import yelpapi
from bs4 import BeautifulSoup
import requests
import time
import os
import json
import re
import fitz  # PyMuPDF
from io import BytesIO
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import random
from sklearn.metrics import accuracy_score
from tabulate import tabulate

# ------------------------------------------------
# This script does = 
# ------------------------------------------------

df = pd.read_csv('../Csv/SipsBarItems.csv', encoding='utf-8')
