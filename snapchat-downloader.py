import requests
import os
import sys
from pathlib import Path
import time
import browser_cookie3
import subprocess
from datetime import datetime, timedelta
import zipfile
import json
import shutil
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import tkinter as tk
from tkinter import filedialog

# ============== KONFIGURACJA ŚCIEŻEK NARZĘDZI ==============
# Ustalamy ścieżkę, w której znajduje się skrypt/exe, aby poprawnie odwoływać się do narzędzi
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

EXIFTOOL_PATH = BASE_DIR / "exiftool.exe"
FFMPEG_PATH = BASE_DIR / "ffmpeg.exe"
FFPROBE_PATH = BASE_DIR / "ffprobe.exe"

VERBOSE = True
MAX_WORKERS = 8
thread_local = threading.local()

# ============== FUNKCJE POMOCNICZE ==============

def check_dependencies():
    """Sprawdza, czy potrzebne pliki .exe znajdują się w folderze ze skryptem."""
    missing = []
    if not EXIFTOOL_PATH.exists(): missing.append("exiftool.exe")
    if not FFMPEG_PATH.exists(): missing.append("ffmpeg.exe")
    if not FFPROBE_PATH.exists(): missing.append("ffprobe.exe")
    
    if missing:
        print("⚠ BŁĄD: Brakuje wymaganych plików w folderze programu!")
        for m in missing:
            print(f" - {m}")
        print("\nUpewnij się, że rozpakowałeś wszystkie pliki z paczki.")
        input("\nNaciśnij Enter, aby zakończyć...")
        sys.exit(1)

def select_html_file():
    """Wyswietla okienko wyboru pliku HTML."""
    root = tk.Tk()
    root.withdraw() # Ukrywa główne puste okno
    file_path = filedialog.askopenfilename(
        title="Wybierz plik memories_history.html ze Snapchata",
        filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
    )
    return file_path

def detect_file_type(content):
    first_bytes = content[:12] if len(content) >= 12 else b''
    if first_bytes[:4] in [b'PK\x03\x04', b'PK\x05\x06']: return '.zip'
    if len(first_bytes) >= 8 and first_bytes[4:8] == b'ftyp':
        if len(first_bytes) >= 12 and first_bytes[8:12] in [b'qt  ', b'mdat']:
            return '.mov'
        return '.mp4'
    if first_bytes[:4] == b'\x1a\x45\xdf\xa3': return '.webm'
    if first_bytes[:2] == b'\xff\xd8': return '.jpg'
    if first_bytes[:8] == b'\x89PNG\r\n\x1a\n': return '.png'
    if first_bytes[:6] in [b'GIF87a', b'GIF89a']: return '.gif'
    return '.unknown'

def get_video_dimensions(filepath):
    try:
        cmd = [str(FFPROBE_PATH), '-v', 'quiet', '-print_format', 'json', '-show_streams', str(filepath)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    return stream.get('width'), stream.get('height')
    except Exception:
        pass
    return None, None

def set_file_metadata(filepath, memory):
    try:
        if filepath.suffix in ['.zip', '.unknown']:
            return False
        
        # Przetwarzanie i PRZESUNIĘCIE CZASU o +2 godziny w locie
        date_str = memory['date']
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S UTC')
        dt = dt + timedelta(hours=2) # <--- Przesunięcie czasu zaimplementowane tutaj
        exif_date = dt.strftime('%Y:%m:%d %H:%M:%S')
        
        is_video = filepath.suffix.lower() in ['.mp4', '.mov', '.webm']
        cmd = [str(EXIFTOOL_PATH), '-overwrite_original']
        
        if is_video:
            cmd.extend(['-api', 'QuickTimeUTC'])
            cmd.extend([
                f'-CreateDate={exif_date}',
                f'-ModifyDate={exif_date}',
                f'-MediaCreateDate={exif_date}',
                f'-TrackCreateDate={exif_date}',
                f'-FileCreateDate={exif_date}',
                f'-FileModifyDate={exif_date}',
            ])
        else:
            cmd.extend([
                f'-DateTimeOriginal={exif_date}',
                f'-CreateDate={exif_date}',
                f'-ModifyDate={exif_date}',
            ])
            
        location = memory['location']
        if 'Latitude, Longitude:' in location:
            coords = location.split('Latitude, Longitude:')[1].strip()
            lat, lon = [x.strip() for x in coords.split(',')]
            lat_f, lon_f = float(lat), float(lon)
            cmd.extend([
                f'-GPSLatitude={abs(lat_f)}',
                f'-GPSLongitude={abs(lon_f)}',
                f'-GPSLatitudeRef={"N" if lat_f >= 0 else "S"}',
                f'-GPSLongitudeRef={"E" if lon_f >= 0 else "W"}',
            ])
            
        cmd.append(str(filepath))
        # Puszczenie komendy (ukryte okienko cmd dla windowsa)
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        
        return result.returncode == 0
    except Exception as e:
        return False

def merge_overlay(main_path, overlay_path, output_path):
    try:
        main_w, main_h = get_video_dimensions(main_path)
        if not main_w or not main_h:
            return False
            
        is_video = main_path.suffix.lower() in ['.mp4', '.mov', '.webm']
        if is_video:
            cmd = [
                str(FFMPEG_PATH), '-v', 'error', '-i', str(main_path), '-i', str(overlay_path),
                '-filter_complex', f'[1:v]scale={main_w}:{main_h}[ovr];[0:v][ovr]overlay=0:0:format=auto',
                '-c:v', 'libx264', '-preset', 'fast', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-y', str(output_path)
            ]
        else:
            cmd = [
                str(FFMPEG_PATH), '-v', 'error', '-i', str(main_path), '-i', str(overlay_path),
                '-filter_complex', f'[1:v]scale={main_w}:{main_h}[ovr];[0:v][ovr]overlay=0:0:format=auto',
                '-c:v', 'mjpeg', '-q:v', '2', '-y', str(output_path)
            ]
            
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return result.returncode == 0
    except Exception:
        return False

def process_zip(zip_path, output_index, memory, output_dir):
    temp_dir = output_dir / f"temp_{output_index}"
    temp_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(temp_dir)
        
    main_files = list(temp_dir.glob("*-main.*"))
    overlay_files = list(temp_dir.glob("*-overlay.png"))
    
    if not main_files:
        shutil.rmtree(temp_dir)
        return None
        
    main_file = main_files[0]
    ext = main_file.suffix
    output_path = output_dir / f"{output_index:03d}{ext}"
    
    if not overlay_files:
        shutil.copy(main_file, output_path)
        shutil.rmtree(temp_dir)
        if zip_path.exists():
            os.remove(zip_path)
        return output_path
        
    overlay_file = overlay_files[0]
    if merge_overlay(main_file, overlay_file, output_path):
        shutil.rmtree(temp_dir)
        if zip_path.exists():
            os.remove(zip_path)
        return output_path
        
    shutil.rmtree(temp_dir)
    if zip_path.exists():
        os.remove(zip_path)
    return None

def download_memory(memory, index, session, output_dir):
    try:
        url = memory['download_url']
        ext_guess = '.mp4' if 'video' in memory['media_type'].lower() else '.jpg'
        filename_check = output_dir / f"{index:03d}{ext_guess}"
        
        # Pomijanie istniejących plików
        if filename_check.exists() and filename_check.stat().st_size > 0:
            return True, "Zignorowano (już istnieje)"
            
        response = session.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Referer': 'https://accounts.snapchat.com/',
        })
        response.raise_for_status()
        
        ext = detect_file_type(response.content)
        if ext == '.zip':
            temp_zip = output_dir / f"temp_{index}.zip"
            with open(temp_zip, 'wb') as f:
                f.write(response.content)
            final_path = process_zip(temp_zip, index, memory, output_dir)
            if final_path:
                set_file_metadata(final_path, memory)
            return (final_path is not None), "Zakończono z ZIP"
            
        filepath = output_dir / f"{index:03d}{ext}"
        with open(filepath, 'wb') as f:
            f.write(response.content)
        set_file_metadata(filepath, memory)
        return True, "Pobrano"
        
    except Exception as e:
        return False, str(e)

def get_thread_session(cookies):
    if not hasattr(thread_local, 'session'):
        thread_local.session = requests.Session()
        if cookies:
            thread_local.session.cookies = cookies
    return thread_local.session

def download_task(index, memory, cookies, output_dir):
    success, message = download_memory(memory, index, get_thread_session(cookies), output_dir)
    return index, memory, success, message

# ============== GŁÓWNA LOGIKA ==============

def main():
    print("🎯 SNAPCHAT DOWNLOADER PRO (Wielowątkowy)")
    print("=========================================\n")
    
    check_dependencies()
    
    print("Wybierz plik 'memories_history.html' w oknie, które się pojawiło...")
    html_path = select_html_file()
    
    if not html_path:
        print("Nie wybrano pliku. Zamykanie programu.")
        input("\nNaciśnij Enter, aby zakończyć...")
        return

    print(f"\nWybrany plik: {html_path}")
    now = datetime.now().strftime('%Y%m%d-%H%M')
    output_dir = Path(html_path).parent / f"memories-{now}"
    output_dir.mkdir(exist_ok=True)
    
    print(f"🔍 Parsowanie HTML... (zapis w: {output_dir})")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except Exception as e:
        print(f"Błąd odczytu pliku: {e}")
        input("\nNaciśnij Enter, aby zakończyć...")
        return

    tbody = soup.find("tbody")
    rows = tbody.find_all("tr") if tbody else []
    memories = []
    
    for row in rows:
        try:
            cells = row.find_all("td")
            if len(cells) >= 4:
                date = cells[0].text.strip()
                media_type = cells[1].text.strip()
                location = cells[2].text.strip()
                download_cell = cells[3]
                link_tag = download_cell.find("a")
                if link_tag and "href" in link_tag.attrs:
                    onclick = link_tag.get("onclick", "")
                    url_match = re.search(r"downloadMemories\('([^']+)'", onclick)
                    if url_match:
                        download_url = url_match.group(1)
                        memories.append({
                            "date": date,
                            "media_type": media_type,
                            "location": location,
                            "download_url": download_url,
                            "status": download_cell.text.strip(),
                        })
        except Exception:
            continue

    print(f"✓ Znaleziono {len(memories)} memories.\n")
    
    print("🍪 Ładowanie ciasteczek przeglądarki...")
    try:
        cookies = browser_cookie3.chrome(domain_name='snapchat.com')
        print("✓ Załadowano ciasteczka z Chrome.\n")
    except Exception as e:
        print(f"⚠ Ostrzeżenie ciasteczek (upewnij się, że jesteś zalogowany w Chrome na Snapchacie): {e}\n")
        cookies = None

    print(f"📁 Folder wyjściowy: {output_dir.absolute()}")
    print(f"🚀 Rozpoczynam pobieranie ({MAX_WORKERS} wątków jedocześnie)...\n")

    # Pierwsze podejście
    failed_memories = []
    ok_count = 0
    
    jobs = [(i, mem) for i, mem in enumerate(memories, 1)]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {executor.submit(download_task, i, mem, cookies, output_dir): i for i, mem in jobs}
        for future in as_completed(future_to_idx):
            idx, mem, success, msg = future.result()
            if success:
                ok_count += 1
                if VERBOSE: print(f"[{idx:04d}/{len(memories)}] ✅ Sukces")
            else:
                failed_memories.append((idx, mem))
                if VERBOSE: print(f"[{idx:04d}/{len(memories)}] ❌ Błąd")

    # Drugie podejście (ponowienie błędu)
    if failed_memories:
        print(f"\n⚠️ Nie udało się pobrać {len(failed_memories)} plików.")
        print("⏳ Rozpoczynam jednorazowe PONAWIANIE (w trybie pojedynczym, aby uniknąć przeciążenia)...\n")
        
        still_failed = []
        for idx, mem in failed_memories:
            print(f"⬇️  Ponawianie #{idx}...")
            success, msg = download_memory(mem, idx, requests.Session() if not cookies else requests.Session(), output_dir)
            if success:
                ok_count += 1
                print(f"    ✅ Naprawiono i pobrano.")
            else:
                still_failed.append(idx)
                print(f"    ❌ Nadal błąd: {msg}")
    else:
        still_failed = []

    # Raport końcowy
    print(f"\n{'='*50}")
    print("📊 RAPORT KOŃCOWY:")
    print(f"✅ Pobrano pomyślnie: {ok_count} z {len(memories)}")
    
    if still_failed:
        print(f"❌ Ostatecznie odrzucone (nieudane): {len(still_failed)}")
        print(f"Lista numerów z błędami: {still_failed}")
    else:
        print("🏆 100% plików zostało pomyślnie pobranych i przetworzonych!")
        
    print(f"\n📁 Twoje pliki czekają w: {output_dir.absolute()}")
    print(f"{'='*50}\n")
    
    input("Naciśnij Enter, aby zamknąć program...")

if __name__ == "__main__":
    main()