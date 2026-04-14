import re

def extract_us_ids(message):
    return re.findall(r"[A-Z]+-\d+", message)
