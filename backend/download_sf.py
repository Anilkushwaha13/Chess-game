import urllib.request
import zipfile
import os

url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-windows-x86-64-avx2.zip"
zip_path = "stockfish.zip"
extract_dir = "stockfish_bin"

print("Downloading Stockfish...")
urllib.request.urlretrieve(url, zip_path)
print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)
print("Done!")
