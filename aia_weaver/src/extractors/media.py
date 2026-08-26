import html
import json
import os
import struct
import subprocess
import hashlib
from pathlib import Path

from extractors.formatting import format_duration, format_dot_list, format_meta_row, is_generic_or_empty


def _get_file_hash(path: Path) -> str:
    """Compute SHA256 file hash in chunks."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _run_ffprobe(path: Path) -> dict | None:
    """Run ffprobe on a file path with safe subprocess handling and JSON decoding."""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5, shell=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError, OSError, ValueError, KeyError):
        pass
    return None


def _generate_audio_waveform(path: Path) -> list[float]:
    """Generates a normalized 64-point amplitude array (floats 0.0 to 1.0)."""
    try:
        cmd = ["ffmpeg", "-v", "quiet", "-i", str(path), "-ac", "1", "-ar", "1000", "-f", "s16le", "-"]
        proc = subprocess.run(cmd, capture_output=True, timeout=5, shell=False)
        if proc.returncode == 0 and proc.stdout:
            data = proc.stdout
            num_samples = len(data) // 2
            if num_samples > 0:
                samples = struct.unpack(f"<{num_samples}h", data)
                chunk_size = len(samples) / 64.0
                raw_waveform = []
                for i in range(64):
                    start_idx = int(i * chunk_size)
                    end_idx = int((i + 1) * chunk_size)
                    chunk = samples[start_idx:end_idx]
                    peak = max(abs(s) for s in chunk) / 32768.0 if chunk else 0.0
                    raw_waveform.append(peak)

                max_amp = max(raw_waveform) if raw_waveform else 0.0
                if max_amp > 0:
                    return [round(min(1.0, max(0.0, float(amp / max_amp))), 4) for amp in raw_waveform]
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ValueError, struct.error):
        pass

    return [0.0] * 64



def extract_audio(path: Path | str, file_hash: str | None = None) -> tuple[str, str, dict | None]:
    """
    Extract metadata and vector waveform from an audio file using ffprobe / ffmpeg (or mutagen fallback).
    Returns ("AUDIO", formatted_snippet, {"waveform": waveform_list, "duration": duration_sec}).
    """
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        return "AUDIO", "Audio File | File not found", {"waveform": [0.0] * 64, "duration": 0.0}

    duration_sec = 0.0
    bitrate_str = ""
    artist = ""
    title = p.stem
    ffprobe_success = False

    sample_rate_str = None
    pcm_spec_str = None
    channels_str = None
    codec_name = ""

    info = _run_ffprobe(p)
    if info:
        fmt = info.get("format", {})
        streams = info.get("streams", [])

        if "duration" in fmt:
            duration_sec = float(fmt["duration"])
        elif streams and "duration" in streams[0]:
            duration_sec = float(streams[0]["duration"])

        raw_br = fmt.get("bit_rate") or (streams[0].get("bit_rate") if streams else None)
        if raw_br:
            try:
                bitrate_str = f"{int(raw_br) // 1000} kbps"
            except (ValueError, TypeError):
                pass

        tags = fmt.get("tags", {})
        if not tags and streams:
            tags = streams[0].get("tags", {})
        tags_lower = {k.lower(): v for k, v in tags.items()} if tags else {}

        if "title" in tags_lower and tags_lower["title"]:
            title = str(tags_lower["title"])
        if "artist" in tags_lower and tags_lower["artist"]:
            artist = str(tags_lower["artist"])

        if streams:
            astream = streams[0]
            codec_name = (astream.get("codec_name") or "").lower()
            sr = astream.get("sample_rate")
            if sr:
                try:
                    sr_khz = float(sr) / 1000.0
                    sample_rate_str = f"{int(sr_khz)} kHz" if sr_khz.is_integer() else f"{sr_khz:.1f} kHz"
                except (ValueError, TypeError):
                    pass

            ch = astream.get("channels")
            if ch:
                try:
                    ch_num = int(ch)
                    channels_str = "Mono" if ch_num == 1 else ("Stereo" if ch_num == 2 else f"{ch_num} ch")
                except (ValueError, TypeError):
                    pass

            bits = astream.get("bits_per_raw_sample") or astream.get("bits_per_sample")
            sample_fmt = str(astream.get("sample_fmt") or "")
            if not bits:
                if "16" in sample_fmt:
                    bits = "16"
                elif "24" in sample_fmt:
                    bits = "24"
                elif "32" in sample_fmt:
                    bits = "32"

            if codec_name.startswith("pcm_"):
                pcm_spec_str = f"{bits}-bit PCM" if bits and str(bits) != "0" else "PCM"
            elif codec_name == "flac":
                pcm_spec_str = f"{bits}-bit FLAC" if bits and str(bits) != "0" else "FLAC"
            elif codec_name == "alac":
                pcm_spec_str = f"{bits}-bit ALAC" if bits and str(bits) != "0" else "ALAC"
            elif bits and str(bits) != "0":
                pcm_spec_str = f"{bits}-bit"

        ffprobe_success = True
    else:
        ffprobe_success = False

    if not ffprobe_success:
        try:
            import mutagen
            audio_meta = mutagen.File(str(p))
            if audio_meta is not None:
                if hasattr(audio_meta.info, "length") and audio_meta.info.length:
                    duration_sec = float(audio_meta.info.length)
                if hasattr(audio_meta.info, "bitrate") and audio_meta.info.bitrate:
                    bitrate_str = f"{int(audio_meta.info.bitrate) // 1000} kbps"
                if getattr(audio_meta, "tags", None):
                    if "title" in audio_meta.tags:
                        title = str(audio_meta.tags["title"][0])
                    if "artist" in audio_meta.tags:
                        artist = str(audio_meta.tags["artist"][0])
                if hasattr(audio_meta.info, "sample_rate") and audio_meta.info.sample_rate:
                    sr_khz = float(audio_meta.info.sample_rate) / 1000.0
                    sample_rate_str = f"{int(sr_khz)} kHz" if sr_khz.is_integer() else f"{sr_khz:.1f} kHz"
                if hasattr(audio_meta.info, "channels") and audio_meta.info.channels:
                    ch_num = int(audio_meta.info.channels)
                    channels_str = "Mono" if ch_num == 1 else ("Stereo" if ch_num == 2 else f"{ch_num} ch")
                if hasattr(audio_meta.info, "bits_per_sample") and audio_meta.info.bits_per_sample:
                    bits = audio_meta.info.bits_per_sample
                    pcm_spec_str = f"{bits}-bit"
        except (ImportError, Exception):
            pass

    waveform = _generate_audio_waveform(p)

    snippet_parts = []

    if title and not is_generic_or_empty(title):
        snippet_parts.append(f"<span class='title'>{html.escape(title)}</span>")

    artist_row = format_meta_row("Artist:", html.escape(artist) if artist else None)
    if artist_row:
        snippet_parts.append(artist_row)

    meta_items = []

    dur_str = format_duration(duration_sec) if duration_sec > 0 else ""
    dur_row = format_meta_row("Duration:", dur_str)
    if dur_row:
        meta_items.append(dur_row)

    br_row = format_meta_row("Bitrate:", bitrate_str)
    if br_row:
        meta_items.append(br_row)

    ext = p.suffix.lower()
    is_lossless = ext in (".wav", ".flac", ".alac", ".aiff", ".pcm") or (
        codec_name and (codec_name.startswith("pcm_") or codec_name in ("flac", "alac", "wavpack", "ape"))
    )
    if is_lossless:
        tech_spec = format_dot_list(sample_rate_str, pcm_spec_str, channels_str)
        if tech_spec:
            meta_items.append(tech_spec)

    meta_line = format_dot_list(*meta_items)
    if meta_line:
        snippet_parts.append(meta_line)

    formatted_snippet = "<br/>".join(snippet_parts)
    if not formatted_snippet:
        formatted_snippet = f"<span class='title'>{html.escape(p.stem)}</span>"

    payload = {
        "waveform": waveform,
        "duration": round(duration_sec, 2)
    }
    return "AUDIO", formatted_snippet, payload


def extract_video(path: Path | str, file_hash: str | None = None) -> tuple[str, str, str | None]:
    """
    Extract stream metadata and WebP poster thumbnail from a video file using ffprobe / ffmpeg.
    Returns ("VIDEO", formatted_snippet, poster_cache_path).
    """
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        return "VIDEO", "Video File | File not found", None

    duration_sec = 0.0
    res_str = ""
    codec = ""
    fps_str = ""

    info = _run_ffprobe(p)
    if info:
        fmt = info.get("format", {})
        streams = info.get("streams", [])

        if "duration" in fmt:
            duration_sec = float(fmt["duration"])
        elif streams and "duration" in streams[0]:
            duration_sec = float(streams[0]["duration"])

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        if video_stream:
            codec = video_stream.get("codec_name", "")
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            if height == 2160 or width >= 3840:
                res_str = "4K"
            elif height == 1080:
                res_str = "1080p"
            elif height == 720:
                res_str = "720p"
            elif height == 480:
                res_str = "480p"
            elif height > 0:
                res_str = f"{height}p"

            r_fps = video_stream.get("r_frame_rate") or video_stream.get("avg_frame_rate", "")
            if "/" in r_fps:
                try:
                    num, den = map(float, r_fps.split("/"))
                    if den != 0:
                        fps_val = round(num / den, 2)
                        fps_str = f"{int(fps_val)} fps" if fps_val.is_integer() else f"{fps_val:.2f} fps"
                except (ValueError, ZeroDivisionError):
                    pass
            elif r_fps:
                try:
                    fps_val = float(r_fps)
                    fps_str = f"{int(fps_val)} fps" if fps_val.is_integer() else f"{fps_val:.2f} fps"
                except ValueError:
                    pass

    poster_cache_path = None
    try:
        cache_dir = Path.home() / ".cache" / "aether" / "media"
        cache_dir.mkdir(parents=True, exist_ok=True)

        if not file_hash:
            file_hash = _get_file_hash(p)

        target_poster = cache_dir / f"{file_hash}.webp"
        if target_poster.exists() and target_poster.stat().st_size > 0:
            poster_cache_path = str(target_poster)
        else:
            seek_offset = f"{min(1.0, duration_sec * 0.1):.2f}" if duration_sec > 0 else "1.0"
            ff_cmd = [
                "ffmpeg", "-v", "quiet",
                "-ss", seek_offset,
                "-i", str(p),
                "-vframes", "1",
                "-vf", "scale=256:-1",
                "-c:v", "libwebp",
                "-quality", "80",
                "-y", str(target_poster)
            ]
            ff_proc = subprocess.run(ff_cmd, capture_output=True, timeout=5, shell=False)
            if ff_proc.returncode == 0 and target_poster.exists() and target_poster.stat().st_size > 0:
                poster_cache_path = str(target_poster)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        poster_cache_path = None

    dur_str = format_duration(duration_sec) if duration_sec > 0 else ""

    res_row = format_meta_row("Resolution:", res_str)
    codec_row = format_meta_row("Codec:", html.escape(codec) if codec else None)
    dur_row = format_meta_row("Duration:", dur_str)
    fps_row = format_meta_row("FPS:", fps_str)

    formatted_snippet = format_dot_list(res_row, codec_row, dur_row, fps_row)
    if not formatted_snippet:
        formatted_snippet = "VIDEO | Resolution: Unknown | Codec: Unknown"

    return "VIDEO", formatted_snippet, poster_cache_path
