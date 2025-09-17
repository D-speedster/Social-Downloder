from pytube import YouTube
from pathlib import Path

url = "https://www.youtube.com/watch?v=7fJ36M4H_wc"
print("[YT] Initializing...")
yt = YouTube(url)
print(f"[YT] Title: {yt.title}")
stream = yt.streams.filter(only_audio=True, mime_type="audio/mp4").first()
if stream is None:
    stream = yt.streams.get_lowest_resolution()
    out_name = "yt_test.mp4"
else:
    out_name = "yt_test.m4a"
print(f"[YT] Selected stream: itag={stream.itag}, abr/res={getattr(stream, 'abr', getattr(stream, 'resolution', 'n/a'))}, size={stream.filesize or 'n/a'}")
output_dir = Path("Downloads")
output_dir.mkdir(exist_ok=True)
print("[YT] Downloading...")
stream.download(output_path=str(output_dir), filename=out_name)
print(f"[YT] Download finished -> {output_dir/out_name}")