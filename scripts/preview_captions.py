"""Render diagnostic subtitle samples with real libass at full and phone size.

Usage: python scripts/preview_captions.py [scratch_output_dir]
This uses synthetic backgrounds/text, not a production episode or TTS.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

from caption_policy import resolve_policy, wrap_lines
from export_ass import write_static_ass

SAMPLES = {
    'en': 'The rent is due, but your market stall has sold nothing.',
    'ja': '家賃の期限は来ましたが、店の商品はまだ売れていません。',
    'vi': 'Tiền thuê nhà vẫn đến hạn, dù quầy hàng chưa bán được gì.',
}


def run(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    background = Image.new('RGB', (1920, 1080), '#C4D9D3')
    draw = ImageDraw.Draw(background)
    # Alternating light/dark props test contrast without a full-frame caption strip.
    for x in range(0, 1920, 160):
        draw.rectangle((x, 650, x+120, 1080), fill='#739D99')
        draw.rectangle((x+20, 710, x+100, 760), fill='#F8ECD7')
    for y in range(120, 620, 100):
        draw.line((0, y, 1920, y), fill='#95B8AC', width=5)
    draw.rectangle((520, 190, 1300, 570), fill='#E8CB8A', outline='#466A61', width=10)
    background_path = os.path.join(output_dir, 'test-background.png')
    background.save(background_path)
    label_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
    sheet = Image.new('RGB', (720, 1140), '#F2F4F7')
    labels = ImageDraw.Draw(sheet)
    labels.text((20, 12), 'Previous: 60px', fill='#17212B', font=label_font)
    labels.text((380, 12), f"New: {resolve_policy({}, 'en')['font_size']}px / language font", fill='#17212B', font=label_font)
    reports = []
    for index, (language, text) in enumerate(SAMPLES.items()):
        for column, variant in enumerate(('previous', 'new')):
            folder = os.path.join(output_dir, language, variant)
            os.makedirs(folder, exist_ok=True)
            cfg = resolve_policy({}, language)
            if variant == 'previous':
                cfg.update(font='Arial', font_size=60, margin_v=86, margin_h=96,
                           outline=3, shadow=1, outline_color='&H00000000')
                lines = [text] if len(text) <= 42 else [text[:text.rfind(' ', 0, 42)], text[text.rfind(' ', 0, 42)+1:]]
                if language == 'ja':
                    lines = [text]
            else:
                # The sample can span multiple cues when the CJK line cap requires it.
                from caption_policy import split_phrases
                text_parts = split_phrases(text, cfg)
                lines = wrap_lines(text_parts[0], cfg)
            data = {'fingerprint': 'diagnostic-preview', 'policy': cfg,
                    'language': language, 'beats': [],
                    'qa': {'status': 'pass', 'errors': [], 'warnings': []},
                    'cues': [{'text': ('' if language == 'ja' else ' ').join(lines), 'lines': lines, 'start': 0, 'end': 7}]}
            ass = write_static_ass(folder, data)
            path = os.path.join(folder, 'preview-1080p.png')
            cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'info', '-y', '-i', background_path,
                   '-vf', 'subtitles=filename=final-captions.ass', '-frames:v', '1', '-threads', '2', path]
            result = subprocess.run(cmd, cwd=folder, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode:
                raise RuntimeError(result.stderr[-2000:])
            with open(os.path.join(folder, 'libass-log.txt'), 'w', encoding='utf-8') as handle:
                handle.write(result.stderr)
            with Image.open(path) as rendered:
                phone = rendered.resize((320, 180), Image.Resampling.LANCZOS)
                phone.save(os.path.join(folder, 'preview-phone.png'))
                sheet.paste(phone, (20+360*column, 78+212*index))
            reports.append({'language': language, 'variant': variant, 'font': cfg['font'],
                            'font_size': cfg['font_size'], 'lines': lines, 'image': path})
        labels.text((20, 50+212*index), language.upper(), fill='#17212B', font=label_font)
    comparison = os.path.join(output_dir, 'phone-comparison.png')
    sheet.save(comparison)
    with open(os.path.join(output_dir, 'preview-report.json'), 'w', encoding='utf-8') as handle:
        json.dump({'scope': 'Synthetic diagnostic; not narration timing QA or a Netflix certification.',
                   'phone_size': [320, 180], 'samples': reports}, handle, ensure_ascii=False, indent=2)
    print('Phone comparison:', comparison)
    return comparison


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run(os.path.abspath(sys.argv[1]) if len(sys.argv)>1 else os.path.join(root, 'tmp', 'caption-readability-preview'))
