"""Build the explicitly non-production visual QA prompts; no episode gate bypass."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from animation_prompts import compose_animation_frame_prompt, resolve_people_policy
from codex_prompts import reference_images


def build():
    doc = json.loads((HERE/'sequence.json').read_text(encoding='utf-8'))
    assert doc['test_kind'] == 'nonproduction_visual_acceptance'
    rows=[]
    for beat in doc['beats']:
        for shot in beat['shots']:
            key=beat['id']+shot['id']
            prompt=compose_animation_frame_prompt(doc,beat,shot)
            path=HERE/'prompts'/f'{key}.txt'
            path.parent.mkdir(exist_ok=True)
            path.write_text(prompt+'\n',encoding='utf-8')
            rows.append({'key':key,'test_kind':doc['test_kind'],
                         'narration_span':beat['narration_span'],
                         'people_policy':resolve_people_policy(shot),
                         'visual_intent':shot['visual_intent'],
                         'prompt_file':f'prompts/{key}.txt',
                         'save_as':f'images/{key}.png',
                         'image_status':'needs_review' if (HERE/'images'/f'{key}.png').is_file() else 'not_generated',
                         'reference_images':reference_images(doc,shot)})
    (HERE/'sample-manifest.json').write_text(json.dumps({'test_kind':doc['test_kind'],'narration_version':doc['narration_version'],'assets':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Built {len(rows)} non-production QA prompts. No audio, media registration or production approval is implied.')
    return rows


if __name__=='__main__':
    build()
