"""Build the reel: synthesise audio, render every frame in parallel, encode an
iPhone-ready vertical H.264/AAC MP4.

    python3 make.py            # -> out/claude_motion_reel.mp4
"""
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import imageio_ffmpeg

import audio
import render
from lib import DURATION, H, W

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def main():
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, "reel.wav")
    mp4 = os.path.join(OUT, "claude_motion_reel.mp4")
    print("audio ...", flush=True)
    audio.write_wav(wav)

    frames = int(round(DURATION * render.FPS))
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(render.FPS), "-i", "-",
           "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "24M", "-bufsize", "48M", "-profile:v", "high", "-level", "4.2",
           "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
           "-shortest", "-movflags", "+faststart", "-tag:v", "avc1", mp4]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(os.cpu_count()) as pool:
        for i, frame in enumerate(pool.imap(render.render_frame, range(frames), chunksize=4)):
            enc.stdin.write(frame.tobytes())
            if i % 60 == 0:
                print("frame %d/%d  %.0fs" % (i, frames, time.time() - t0), flush=True)
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("ffmpeg failed")
    print("wrote", mp4)


if __name__ == "__main__":
    main()
