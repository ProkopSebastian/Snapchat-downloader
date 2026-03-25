Snapchat Memories Downloader
A Python-based utility to automate the downloading of your Snapchat memories using the data export provided by Snapchat. This tool processes the memories_history.html file, handles media downloads, and restores original metadata.

Key Features
Parallel Downloading: Uses multiple threads to handle the download queue more efficiently than a single-threaded approach.

Overlay Processing: Automatically detects and merges Snapchat filters/overlays into your photos and videos using FFmpeg.

Metadata Restoration: Writes the original capture date and GPS coordinates directly into the files (EXIF) using ExifTool.

Timezone Offset: Automatically applies a +2h offset to match local time during the metadata write process.

Simple GUI: Includes a file picker to easily select your Snapchat HTML export without editing the code.

🚀 How to use (Pre-compiled version)
If you are using the .exe version from the Releases tab:

Log in to Snapchat in your Google Chrome browser (required for authentication cookies).

Request and download your data from Snapchat, then extract the ZIP archive.

Place snapchat-downloader.exe, exiftool.exe, ffmpeg.exe, and ffprobe.exe in the same folder.

Run the downloader and select your memories_history.html file.

Wait for the process to complete. Your files will be saved in a new folder named Memories_YYYYMMDD.

💻 How to run from source
Clone the repository:

Bash
git clone https://github.com/ProkopSebastian/Snapchat-downloader.git
cd Snapchat-downloader
Install requirements:

Bash
pip install -r requirements.txt
Dependencies: Ensure exiftool.exe, ffmpeg.exe, and ffprobe.exe are present in the root directory.

Run the script:

Bash
python snapchat-downloader.py
Requirements
Python 3.10+

Google Chrome (for session cookies)

External Binaries: ExifTool and FFmpeg

Legal Disclaimer
This tool is for personal use only. Use it responsibly and in accordance with Snapchat's Terms of Service. The authors are not responsible for any account restrictions or data loss.