import json,os,html
root=r'D:\Video\From Need to Tool\why-clay-in-your-pencil'
with open(os.path.join(root,'imagegen','manifest.json'),encoding='utf-8-sig') as f:m=json.load(f)
rows=[]
for a in m['assets']:
 p=os.path.join(root,*a['save_as'].split('\\'))
 if os.path.exists(p):
  purpose=(a.get('visual_intent') or {}).get('purpose','')
  rows.append(f'<figure><img src="../../{html.escape(a["save_as"].replace(chr(92),"/"))}" alt="{html.escape(a["key"])}"><figcaption><b>{html.escape(a["key"])}</b> — {html.escape(purpose)}</figcaption></figure>')
page='''<!doctype html><meta charset="utf-8"><title>Visual review — Why Is There Clay in Your Pencil?</title><style>body{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}h1{font-size:1.7rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:1rem}figure{margin:0;border:1px solid #ddd;padding:.6rem;border-radius:.5rem}img{width:100%;height:auto;display:block}figcaption{padding:.5rem .2rem}</style><h1>Why Is There Clay in Your Pencil? — visual work in progress</h1><p>Chibi 2D stills. The attached opening, mechanism, process, map and ending keyframes are review drafts; the manifest records exact files. Thumbnail preview is linked separately. This gallery is not final image QA.</p><div class="grid">'''+''.join(rows)+'''</div>'''
with open(os.path.join(root,'review','visuals','index.html'),'w',encoding='utf-8') as f:f.write(page)
print(f'gallery: {len(rows)} frames')
