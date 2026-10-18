#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p data/raw
while IFS= read -r url; do
    file="data/raw/${url##*/}"
    curl --retry 3 --fail --location "$url" --output "$file.part"
    mv "$file.part" "$file"
done < data/download_urls.txt
curl --retry 3 --fail --location 'https://www.eac.gov/sites/default/files/2026-02/2024_EAVS_for_Public_Release_nolabel_V2_csv.zip' --output data/raw/eavs2024.zip.part
mv data/raw/eavs2024.zip.part data/raw/eavs2024.zip
curl --retry 3 --fail --location 'https://www.eac.gov/sites/default/files/2025-06/2024_EAVS_Codebook.xlsx' --output data/raw/eavs2024_codebook.xlsx.part
mv data/raw/eavs2024_codebook.xlsx.part data/raw/eavs2024_codebook.xlsx
