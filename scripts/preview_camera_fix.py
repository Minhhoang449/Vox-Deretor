"""Render diagnostic geometry (not episode artwork) with the production camera."""
import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch

from PIL import Image, ImageDraw
import ffmpeg_stills
from image_reuse_qa import build_report
from stills_camera import plan_cameras

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/visual-reuse-camera-fix-2026-10-16'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shots = []
    for i in range(4):
        path = OUT / f'diagnostic-{i}.png'
        image = Image.new('RGB', (640, 360), (236, 239, 234))
        draw = ImageDraw.Draw(image)
        # Edge boxes make unintended cropping of a held frame visible.
        draw.rectangle((1, 1, 638, 358), outline=(155, 35, 30), width=3)
        if i == 0:
            for x in range(30, 610, 65):
                top = 90 + (x % 100)
                draw.rectangle((x, top, x + 40, 310), fill=(40, 90, 120))
            draw.line((15, 320, 625, 320), fill=(30, 50, 45), width=4)
        elif i == 1:
            draw.polygon([(0, 250), (180, 85), (330, 225), (475, 100), (640, 260), (640, 360), (0, 360)], fill=(95, 125, 95))
            draw.rectangle((0, 295, 640, 360), fill=(65, 135, 170))
        elif i == 2:
            draw.rectangle((30, 70, 240, 290), outline=(20, 65, 95), width=5)
            draw.rectangle((390, 70, 610, 290), outline=(20, 65, 95), width=5)
            draw.line((245, 180, 380, 180), fill=(30, 100, 140), width=8)
            draw.polygon([(380, 180), (355, 165), (355, 195)], fill=(30, 100, 140))
            draw.text((42, 82), 'SOURCE', fill=(10, 20, 30))
            draw.text((405, 82), 'DESTINATION', fill=(10, 20, 30))
        else:
            draw.ellipse((210, 70, 430, 290), fill=(125, 115, 65), outline=(40, 45, 35), width=5)
            draw.ellipse((280, 140, 360, 220), fill=(235, 235, 225), outline=(40, 45, 35), width=4)
        image.save(path)
        shots.append({'image':str(path), 'dur':5, 'camera':'auto', 'beat_id':'QA', 'shot_id':str(i),
                      'scene':['Wide city panorama', 'Coastal landscape', 'Labeled flow diagram', 'Close-up of a mechanical joint'][i]})
    shots[0]['camera_direction'] = 'right'
    shots[2]['in_scene_text'] = 'SOURCE; DESTINATION'
    shots.append({**shots[0], 'shot_id':'4', 'reuse_image_from':'QA0'})
    config = ffmpeg_stills.settings()
    if not shutil.which(config['ffmpeg']):
        matches = list((ROOT / '.tools/ffmpeg/unpacked').glob('*/bin/ffmpeg.exe'))
        if not matches:
            raise SystemExit('Configured FFmpeg unavailable; diagnostic source files preserved.')
        config['ffmpeg'] = str(matches[0])
        config['ffprobe'] = str(matches[0].with_name('ffprobe.exe'))
    # Keep configured NVENC codec, preset, CQ, workers and transitions unchanged.
    report = build_report(shots)
    (OUT/'image-reuse-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'camera-plan.json').write_text(json.dumps(plan_cameras(shots,config),ensure_ascii=False,indent=2),encoding='utf-8')
    with patch.object(ffmpeg_stills,'settings',return_value=config):
        result = ffmpeg_stills.render(str(OUT),shots,640,360,24,str(OUT/'camera-preview.mp4'))
        again = ffmpeg_stills.render(str(OUT),shots,640,360,24,str(OUT/'camera-preview-cache-check.mp4'))
    # Contact sheet from the actual encoded preview, once each shot has settled.
    ffmpeg_stills.invoke([config['ffmpeg'],'-y','-hide_banner','-loglevel','error','-ss','2',
        '-i',str(OUT/'camera-preview.mp4'),'-vf',"fps=1/5,scale=320:180,tile=5x1",'-frames:v','1',str(OUT/'contact-sheet.png')])
    summary={'status':'diagnostic render, not production scene QA','pan_zoom_enabled':True,
             'shots':result['shots'],'frames':result['frames'],'cache_reused_shots':again['reused_shots'],
             'preview':str(OUT/'camera-preview.mp4'),'limitations':['Synthetic geometry only; no episode art or narration changed.','Optional Revideo runtime not rendered in this diagnostic.']}
    (OUT/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
