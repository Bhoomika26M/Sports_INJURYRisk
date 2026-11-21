import os
import glob
import subprocess
import imageio_ffmpeg

def transcode_all():
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    if not exe:
        print("FFmpeg not found")
        return

    files = glob.glob(os.path.join("uploads", "annotated_*.mp4"))
    print(f"Found {len(files)} files to check/transcode")
    for f in files:
        # Check codec
        probe = subprocess.run([exe, "-i", f], capture_output=True, text=True)
        if "h264" in probe.stderr.lower():
            print(f"Already H.264: {f}")
            continue

        print(f"Transcoding {f} to H.264...")
        tmp = f + ".h264.mp4"
        cmd = [
            exe, "-y",
            "-i", f,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "23",
            "-movflags", "+faststart",
            tmp
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            os.replace(tmp, f)
            print(f"Successfully converted {f} to H.264")
        else:
            print(f"Failed to convert {f}: {res.stderr}")
            if os.path.exists(tmp):
                os.remove(tmp)

if __name__ == "__main__":
    transcode_all()
