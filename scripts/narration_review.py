"""Build a listening copy and a caption issue queue from EXISTING approved WAVs.

No synthesis, time stretching, BGM, production edits or automatic QA acceptance.
The listening copy joins WAVs directly; caption times refer to the final video,
which has visual tails and therefore a different clock.
"""
import argparse
import html
import json
from pathlib import Path
import shutil
import wave

from cache_keys import file_fingerprint
from narration_lock import beat_speech, digest, inspect, inspect_audio, load_doc


def concatenate_wavs(paths, output):
    """Copy PCM frames verbatim; refuse incompatible streams instead of retiming."""
    paths = [Path(path) for path in paths]
    if not paths:
        raise ValueError("No narration WAVs available.")
    headers, offsets, cursor = [], [], 0.0
    for path in paths:
        with wave.open(str(path), "rb") as src:
            headers.append((src.getnchannels(), src.getsampwidth(), src.getframerate(), src.getcomptype()))
            seconds = src.getnframes()/src.getframerate()
            offsets.append({"audio": str(path), "start": cursor, "end": cursor+seconds})
            cursor += seconds
    if len(set(headers)) != 1 or headers[0][3] != "NONE":
        raise ValueError("Narration WAV formats differ; review voice/settings instead of resampling silently.")
    output = Path(output)
    if output.resolve() in [path.resolve() for path in paths]:
        raise ValueError("Listening copy must not overwrite a source WAV.")
    temporary = output.with_suffix(".wav.tmp")
    try:
        with wave.open(str(temporary), "wb") as dst:
            dst.setnchannels(headers[0][0]); dst.setsampwidth(headers[0][1]); dst.setframerate(headers[0][2])
            for path in paths:
                with wave.open(str(path), "rb") as src:
                    while frames := src.readframes(65536):
                        dst.writeframesraw(frames)
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return offsets


def caption_queue(timeline):
    """Turn reported estimates and speed warnings into exact video seek ranges."""
    qa = timeline.get("qa") or {}
    cues = timeline.get("cues") or []
    result = []
    for identifier in qa.get("estimated_beats", []):
        rows = [cue for cue in cues if cue.get("beat_id") == identifier]
        metadata = next((b for b in timeline.get("beats", []) if b.get("beat_id") == identifier), {})
        if rows:
            result.append({"kind": "estimated_alignment", "beat_id": identifier,
                           "start": min(c["start"] for c in rows), "end": max(c["end"] for c in rows),
                           "text": metadata.get("reason") or "Estimated timing requires listening review."})
    target = float((timeline.get("policy") or {}).get("target_cps", 17))
    maximum = float((timeline.get("policy") or {}).get("max_cps", 20))
    for index, cue in enumerate(cues, 1):
        if float(cue.get("cps", 0)) > target+0.01:
            result.append({"kind": "reading_speed", "beat_id": cue.get("beat_id"),
                           "cue_number": index, "start": cue["start"], "end": cue["end"],
                           "cps": cue["cps"], "above_maximum": cue["cps"] > maximum+0.01,
                           "text": cue["text"]})
    return sorted(result, key=lambda row: (row["start"], row["kind"]))


def build(project_dir, output_dir, middle_beat=None, with_audio=False):
    project, output = Path(project_dir).resolve(), Path(output_dir).resolve()
    if output == project or output in project.parents:
        raise ValueError("Use a separate review output folder, never the production root or its parents.")
    doc = load_doc(project)
    approval = inspect(project, doc)
    if approval["status"] == "blocked":
        raise ValueError("Narration lock mismatch: " + "; ".join(approval["errors"]))
    audio = inspect_audio(project, doc)
    if audio["errors"]:
        raise ValueError("WAV integrity check failed: " + "; ".join(audio["errors"][:3]))
    timeline_path = project/"captions-timeline.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8-sig")) if timeline_path.is_file() else {}
    queue = caption_queue(timeline)
    # Never imply that old caption reports have been newly aligned or accepted.
    content_matches = bool(timeline)
    for beat in doc.get("beats", []):
        joiner = "" if timeline.get("language") == "ja" else " "
        actual = joiner.join(c["text"] for c in timeline.get("cues", []) if c.get("beat_id") == beat.get("id"))
        from caption_policy import normalized_text
        if normalized_text(actual, timeline.get("language", "en")) != normalized_text(beat.get("narration", ""), timeline.get("language", "en")):
            content_matches = False
    beats = [b for b in doc.get("beats", []) if (b.get("narration") or "").strip()]
    if not beats:
        raise ValueError("No narration beats are available.")
    if middle_beat and middle_beat not in {b["id"] for b in beats}:
        raise ValueError("Unknown mechanism beat: " + middle_beat)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "episode_dir": str(project), "channel_id": doc.get("channel_id"),
                "speech_sha256": digest(beat_speech(doc)), "approval": approval, "audio_check": audio,
                "caption_report_scope": "Existing report; not newly aligned or listening-approved.",
                "caption_text_matches_beats": content_matches,
                "caption_source": file_fingerprint(str(timeline_path), True),
                "caption_qa": timeline.get("qa"), "caption_queue": queue,
                "listening_review_status": "pending", "clips": [], "listening_offsets": []}
    if with_audio:
        paths = [Path(row["audio"]) for row in audio["beats"]]
        manifest["listening_offsets"] = concatenate_wavs(paths, output/"audio-review.wav")
        for beat, row in zip(beats, manifest["listening_offsets"]):
            row["beat_id"] = beat["id"]
        # Three distinct editorial roles; no invented claim of which middle is hardest.
        middle = next((b for b in beats if b["id"] == middle_beat), beats[len(beats)//2])
        for role, beat in (("opening", beats[0]), ("mechanism", middle), ("ending", beats[-1])):
            source = next(Path(row["audio"]) for row in audio["beats"] if row["beat_id"] == beat["id"])
            destination = output/(role+".wav")
            if destination.resolve() == source.resolve():
                raise ValueError("Review clip must not overwrite its source.")
            shutil.copyfile(source, destination)
            manifest["clips"].append({"role": role, "beat_id": beat["id"], "file": destination.name,
                                      "narration": beat["narration"]})
    (output/"review.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    write_html(manifest, output, project/"final.mp4")
    return manifest


def write_html(data, output, video):
    esc = html.escape
    video_panel = (f'<video id="film" controls preload="metadata" src="{esc(video.as_uri(), quote=True)}"></video>'
                   if video.is_file() else '<p>Chưa có video cuối để đối chiếu.</p>')
    audio_panel = ('<h2>Bản nghe liên tục từ WAV hiện có</h2><audio controls preload="metadata" src="audio-review.wav"></audio>'
                   '<p>Giữ nguyên khung âm thanh; không BGM, không đổi tốc độ, không thêm đuôi hình. Mốc phụ đề dưới đây thuộc video cuối.</p>'
                   if data['listening_offsets'] else '')
    clips = ''.join(f'<h3>{esc(c["role"])} · {esc(c["beat_id"])}</h3><audio controls preload="metadata" src="{c["file"]}"></audio><p>{esc(c["narration"])}</p>' for c in data['clips'])
    rows = ''.join(f'<li><button onclick="seek({float(r["start"])})">{float(r["start"]):.2f}s</button> '
                   f'<b>{esc(r["beat_id"] or "?")} · {esc(r["kind"])}</b> {esc(r["text"])}'
                   f'{" · "+str(r["cps"])+" CPS" if "cps" in r else ""}</li>' for r in data['caption_queue'])
    qa = data.get('caption_qa') or {}
    page = f'''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Nghe và kiểm tra phụ đề</title>
<style>body{{font:16px/1.6 system-ui;max-width:1000px;margin:32px auto;padding:0 20px;color:#18242b;background:#f7f8fa}}h1{{font-size:26px}}video{{width:100%;max-height:420px;background:#111}}audio{{width:100%}}li{{margin:14px 0}}button{{padding:5px 9px;cursor:pointer}}small{{overflow-wrap:anywhere}}.notice{{border-left:4px solid #a06010;padding:8px 14px;background:#fff4df}}</style>
<h1>{esc(data.get('channel_id') or '')} · bản kiểm tra</h1>
<p class="notice">Chưa xác nhận nghe/xem. Hãy nghe trực tiếp bản WAV hiện có và tự đánh giá trước khi duyệt.
Phụ đề: {esc(qa.get('status', 'unavailable'))}; {len(qa.get('errors', []))} lỗi; {len(qa.get('warnings', []))} cảnh báo.
Nội dung phụ đề khớp beats: {data['caption_text_matches_beats']}.</p>
{audio_panel}{clips}<h2>Đối chiếu video và phụ đề hiện có</h2>{video_panel}
<p>Mốc là giây trên video cuối. Nút mốc tua sớm 1 giây để nghe ngữ cảnh. Không tự đánh dấu QA đạt.</p>
<ul>{rows}</ul><small>SHA-256 lời: {data['speech_sha256']} · Nguồn: {esc(data['episode_dir'])}</small>
<script>function seek(t){{const p=document.getElementById('film');if(p){{p.currentTime=Math.max(0,t-1);p.play();}}}}</script></html>'''
    (output/"review.html").write_text(page, encoding="utf-8")


def main():
    from local_guard import configure_console
    configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--middle-beat")
    parser.add_argument("--audio", action="store_true", help="Copy full listening WAV and three beat samples")
    args = parser.parse_args()
    result = build(args.project_dir, args.output_dir, args.middle_beat, args.audio)
    print(json.dumps({"review": str(Path(args.output_dir).resolve()/"review.html"),
                      "queue_items": len(result['caption_queue']),
                      "listening_review_status": result['listening_review_status']}, ensure_ascii=False))


if __name__ == "__main__":
    main()
