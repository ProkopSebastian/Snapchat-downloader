# Snapchat Memories Downloader Pro 👻

A multithreaded, automated tool to download all your Snapchat memories from the exported `memories_history.html` file. 

Unlike basic scripts, this tool automatically merges video overlays (using FFmpeg) and restores the original EXIF metadata (creation date, time, and GPS location) using ExifTool, so your photos and videos appear perfectly organized in your gallery.

## Features
- **Multithreaded Downloading:** Extremely fast downloads using multiple concurrent connections.
- **Auto-Overlay Merge:** Automatically detects `.zip` files containing Snapchat filters/overlays and merges them into the main photo/video.
- **EXIF Metadata Restoration:** Fixes file creation dates (with automatic +2h timezone offset) and restores GPS coordinates directly into the file's metadata.
- **Smart Resume:** Skips already downloaded files and automatically retries failed downloads.
- **GUI File Picker:** No need to hardcode paths; simply select your `memories_history.html` file via a native window.

---

## 🚀 How to use (For non-technical users)

You do **not** need to install Python. 

1. Ensure you are logged into Snapchat on your **Google Chrome** browser (the script uses Chrome cookies to authenticate downloads).
2. Request your data from Snapchat and extract the `.zip` they email you.
3. Go to the [Releases page](../../releases) *(replace this with your actual releases link)* and download the latest `Snapchat-Downloader.zip`.
4. Extract the downloaded folder on your PC.
5. Double-click `snapchat-downloader.exe`.
6. When prompted, select your `memories_history.html` file (located in the `html` folder of your Snapchat data export).
7. Wait for the process to finish. Your memories will be saved in a new folder named `Pobrane_Wspomnienia`.

---

## 💻 How to run from source (For developers)

If you prefer to run the Python script directly:

1. Clone this repository:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
   cd YOUR_REPO_NAME