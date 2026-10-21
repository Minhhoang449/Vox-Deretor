"""Localized playlist catalog and explicit per-episode upload assignments.

No account writes or network calls. Recommendations are never saved as choices.
Usage: python scripts/playlists.py list [channel-id]
       python scripts/playlists.py export [output.md]
"""
import json
import os
import re
import sys
import unicodedata

from channels import load_channels, load_archived_channels, resolve
from local_guard import configure_console

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_FILE = os.path.join(ROOT, 'config', 'playlists.json')


def load_catalog(archived=False):
    catalog_path = CATALOG_FILE
    if archived:
        with open(CATALOG_FILE, encoding='utf-8-sig') as handle:
            relative = json.load(handle).get('archived_catalog_file')
        if not relative:
            raise ValueError('No archived playlist catalog is configured.')
        catalog_path = os.path.join(ROOT, relative)
    with open(catalog_path, encoding='utf-8-sig') as handle:
        data = json.load(handle)
    roster = {channel['id']: channel for channel in (load_archived_channels() if archived else load_channels())}
    seen_channels, seen_ids = set(), set()
    limits = data['policy']
    for entry in data['channels']:
        channel_id = entry['channel_id']
        if channel_id not in roster or channel_id in seen_channels:
            raise ValueError(f'Unknown or repeated playlist channel: {channel_id}')
        seen_channels.add(channel_id)
        seen_titles = set()
        for playlist in entry['playlists']:
            key = playlist['id']
            if key in seen_ids or not key.startswith(channel_id+'-'):
                raise ValueError(f'Invalid or repeated playlist key: {key}')
            seen_ids.add(key)
            for field in ('title', 'description', 'include_when', 'label_vi'):
                if not isinstance(playlist.get(field), str) or not playlist[field].strip():
                    raise ValueError(f'Playlist {key} needs {field}.')
            if len(playlist['title']) > limits['editorial_title_limit']:
                raise ValueError(f'Playlist title exceeds the editorial limit: {key}')
            if len(playlist['description']) > limits['editorial_description_limit']:
                raise ValueError(f'Playlist description exceeds the editorial limit: {key}')
            if playlist['title'].casefold() in seen_titles:
                raise ValueError(f'Duplicate playlist title in {channel_id}.')
            seen_titles.add(playlist['title'].casefold())
            if playlist.get('kind') not in ('core', 'specialist'):
                raise ValueError(f'Playlist {key} needs a core/specialist kind.')
            for field in ('keywords', 'required_any'):
                terms = playlist.get(field, [])
                if not isinstance(terms, list) or not all(isinstance(term, str) and term.strip() for term in terms):
                    raise ValueError(f'Playlist {key}: {field} must be a list of nonempty strings.')
            youtube_id = playlist.get('youtube_playlist_id') or ''
            if not isinstance(youtube_id, str) or (youtube_id and not re.fullmatch(r'[A-Za-z0-9_-]{10,}', youtube_id)):
                raise ValueError(f'Playlist {key}: invalid YouTube playlist ID.')
            playlist['language'] = roster[channel_id]['language']
    if seen_channels != set(roster):
        raise ValueError('Playlist catalog must cover every configured channel.')
    return data


def channel_playlists(selector, catalog=None):
    channel = resolve(selector)
    if not catalog or not any(entry['channel_id'] == channel['id'] for entry in catalog['channels']):
        catalog = load_catalog(archived=channel.get('profile_status') == 'archived')
    return next(entry['playlists'] for entry in catalog['channels'] if entry['channel_id'] == channel['id'])


def _normalized(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', str(value)).casefold()
                   if not unicodedata.combining(char))


def _matches(term, text):
    term = _normalized(term)
    pattern = re.escape(term)
    if term and term[0].isascii() and term[0].isalnum():
        pattern = r'(?<![a-z0-9])'+pattern
    if term and term[-1].isascii() and term[-1].isalnum():
        pattern += r'(?![a-z0-9])'
    return bool(re.search(pattern, text))


def recommend_playlists(doc, playlists):
    metadata = doc.get('youtube_metadata') or {}
    selected_id = metadata.get('selected_candidate_id')
    raw_candidates = metadata.get('candidates') or []
    candidates = [entry for entry in raw_candidates if isinstance(entry, dict)] if isinstance(raw_candidates, list) else []
    selected = next((candidate for candidate in candidates if candidate.get('id') == selected_id), None)
    titles = [str(selected.get('title') or '')] if selected else [str(candidate.get('title') or '') for candidate in candidates]
    raw_phrases = metadata.get('search_phrases') or []
    phrases = [value for value in raw_phrases if isinstance(value, str)] if isinstance(raw_phrases, list) else []
    text = _normalized(' '.join([str(doc.get('topic') or ''), str(doc.get('project') or '').replace('-', ' '),
                                str(metadata.get('promise') or ''), *titles,
                                *phrases]))
    recommendations = []
    for playlist in playlists:
        if playlist.get('required_any') and not any(_matches(term, text) for term in playlist['required_any']):
            continue
        matched = [term for term in playlist['keywords'] if _matches(term, text)]
        if not matched:
            continue
        # Specialist evidence ranks above incidental generic terms in a war topic.
        score = len(matched) + (3 if playlist['kind'] == 'specialist' else 0)
        recommendations.append({'id': playlist['id'], 'title': playlist['title'],
                                'label_vi': playlist['label_vi'], 'matched_keywords': matched,
                                'score': score, 'include_when': playlist['include_when']})
    return sorted(recommendations, key=lambda entry: (-entry['score'], entry['id']))[:3]


def episode_playlists(doc):
    channel = resolve(doc.get('channel_id') or '')
    catalog = load_catalog(archived=channel.get('profile_status') == 'archived')
    playlists = channel_playlists(channel['id'], catalog)
    by_id = {playlist['id']: playlist for playlist in playlists}
    raw = (doc.get('youtube_metadata') or {}).get('playlists')
    raw = {} if raw is None else raw
    if not isinstance(raw, dict):
        raise ValueError('youtube_metadata.playlists must be an object.')
    primary_id = raw.get('primary_id') or ''
    additional = raw.get('additional_ids') or []
    reason = raw.get('selection_reason') or ''
    if not isinstance(primary_id, str) or not isinstance(reason, str):
        raise ValueError('Playlist primary_id and selection_reason must be strings.')
    if not isinstance(additional, list) or not all(isinstance(item, str) for item in additional):
        raise ValueError('Playlist additional_ids must be a list of strings.')
    if len(additional) > catalog['policy']['maximum_additional']:
        raise ValueError('Choose at most two additional playlists per episode.')
    keys = ([primary_id] if primary_id else []) + additional
    if len(set(keys)) != len(keys):
        raise ValueError('A playlist cannot be selected twice.')
    if additional and not primary_id:
        raise ValueError('Choose a primary playlist before additional playlists.')
    for key in keys:
        if key not in by_id:
            raise ValueError(f'Playlist {key!r} does not belong to channel {channel["id"]}.')
    chosen = []
    for index, key in enumerate(keys):
        entry = dict(by_id[key])
        youtube_id = entry.get('youtube_playlist_id') or ''
        entry.update(role='primary' if index == 0 else 'additional',
                     youtube_url=f'https://www.youtube.com/playlist?list={youtube_id}' if youtube_id else '',
                     platform_status='id_recorded_unverified' if youtube_id else 'create_or_link_in_studio')
        chosen.append(entry)
    return {'catalog_revision': catalog['revision'], 'channel_id': channel['id'],
            'channel_name': channel['display_name'], 'language': channel['language'],
            'status': 'selected' if primary_id else 'pending_selection',
            'selection_reason': reason.strip(), 'primary_id': primary_id,
            'additional_ids': additional, 'selected': chosen,
            'recommendations': recommend_playlists(doc, playlists),
            'available_playlists': [{'id': p['id'], 'title': p['title'], 'label_vi': p['label_vi'],
                                    'kind': p['kind']} for p in playlists]}


def playlist_text(bundle):
    lines = ['PLAYLIST ASSIGNMENT',
             f"Channel: {bundle['channel_name']} ({bundle['channel_id']}) | Language: {bundle['language']}",
             f"Catalog: {bundle['catalog_revision']}", f"Selection status: {bundle['status']}"]
    if bundle['selected']:
        if bundle['selection_reason']:
            lines.append('Selection reason: '+bundle['selection_reason'])
        for entry in bundle['selected']:
            lines.extend(['', f"{entry['role'].upper()}: {entry['title']}",
                          f"Internal catalog key: {entry['id']}",
                          'YouTube playlist ID: '+(entry['youtube_playlist_id'] or 'PENDING — create or link in YouTube Studio'),
                          'Description (copy to playlist):', entry['description']])
            if entry['youtube_url']:
                lines.append('Playlist URL (ID supplied locally; not verified): '+entry['youtube_url'])
    else:
        lines.extend(['', 'Choose youtube_metadata.playlists.primary_id before assigning the video in Studio.',
                      'Recommendations below are suggestions, not selected playlists.'])
    if bundle['recommendations']:
        lines.extend(['', 'TOPIC-BASED SUGGESTIONS — REVIEW BEFORE SELECTING'])
        for entry in bundle['recommendations']:
            lines.extend([f"- {entry['id']}: {entry['title']}",
                          '  Matched terms: '+', '.join(entry['matched_keywords'])])
    lines.extend(['', 'AVAILABLE PLAYLISTS FOR THIS CHANNEL'])
    lines.extend(f"- {entry['id']}: {entry['title']}" for entry in bundle['available_playlists'])
    return '\n'.join(lines)


def export_episode_playlists(project_dir, bundle):
    for suffix, content in (('txt', playlist_text(bundle)),
                            ('json', json.dumps(bundle, ensure_ascii=False, indent=2))):
        with open(os.path.join(project_dir, 'youtube-playlists.'+suffix), 'w', encoding='utf-8') as handle:
            handle.write(content+'\n')


def export_catalog(path):
    catalog = load_catalog()
    roster = {channel['id']: channel for channel in load_channels()}
    lines = [f"# Bộ danh sách phát cho {len(roster)} kênh đang hoạt động", '',
             f"Bản: {catalog['revision']} · Cập nhật {catalog['updated_on']}", '',
             'Tên và mô tả bên dưới là nội dung có thể sao chép vào YouTube Studio. '
             'Mỗi kênh có năm nhóm nội dung theo DNA và cách kể riêng trong đợt khởi tạo mới. '
             'Đây là đề xuất biên tập, chưa đo lượng tìm kiếm hoặc hiệu quả xếp hạng.', '',
             'Nguồn cấu hình: `config/playlists.json`. File này được tạo bằng `scripts/playlists.py export`; '
             'chỉnh nội dung ở cấu hình rồi xuất lại. Chỉ mở playlist công khai khi đã có video phù hợp.', '']
    lines.extend(['Catalog hiện hành dành cho sáu kênh mới; catalog cũ được lưu riêng để tra cứu tập cũ. '
                  'ID nội bộ không phải ID YouTube. Không tự đổi playlist trên tài khoản.', ''])
    for channel in catalog['channels']:
        profile = roster[channel['channel_id']]
        lines.extend([f"## {profile['display_name']} — {profile['language']}", ''])
        for index, entry in enumerate(channel['playlists'], 1):
            lines.extend([f"### {index}. {entry['title']}", '',
                          f"Góc nội dung: {entry['label_vi']} · {'Nhóm chính' if entry['kind']=='core' else 'Nhánh chuyên đề'}", '',
                          '**Mô tả để sao chép:**', '', entry['description'], '',
                          f"ID nội bộ: `{entry['id']}`", '', f"Chọn khi: {entry['include_when']}", ''])
    lines.extend(['## Khai báo cho từng tập', '',
                  'Chọn một playlist chính và tối đa hai playlist bổ sung có nội dung phù hợp. '
                  'ID nội bộ là khóa cấu hình; `youtube_playlist_id` chỉ điền sau khi tạo hoặc xác minh playlist thật.', '',
                  '```json', json.dumps({'youtube_metadata': {'playlists': {
                      'primary_id': 'vi-sao-noi-nay-water',
                      'additional_ids': ['vi-sao-noi-nay-infrastructure'],
                      'selection_reason': 'Nội dung lần theo hệ thống nước đô thị và công trình cấp nước.'
                  }}}, ensure_ascii=False, indent=2), '```', '',
                  '`export_youtube.py` ghi mục PLAYLISTS vào gói upload và xuất `youtube-playlists.txt` / '
                  '`youtube-playlists.json`. Bản nháp chưa chọn có thể ghi `pending_selection` cùng gợi ý theo chủ đề; '
                  'trước khi giao metadata cuối của video đã hoàn tất, hãy chọn playlist chính phù hợp từ catalog hiện có '
                  'và ghi lựa chọn vào `youtube_metadata.playlists` trong `beats.json`. Gợi ý không tự thành lựa chọn; '
                  'không tạo mục catalog hay playlist YouTube mới cho một tập.', '', '## Nguồn hướng dẫn', ''])
    lines.extend(f"- [{source['title']}]({source['url']})" for source in catalog['sources'])
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines)+'\n')
    print('Playlist catalog:', os.path.abspath(path))


if __name__ == '__main__':
    configure_console()
    command = sys.argv[1] if len(sys.argv)>1 else 'list'
    if command == 'export':
        export_catalog(sys.argv[2] if len(sys.argv)>2 else os.path.join(ROOT, 'references', 'playlist-catalog.md'))
    elif command == 'list':
        catalog = load_catalog()
        selectors = [sys.argv[2]] if len(sys.argv)>2 else [channel['channel_id'] for channel in catalog['channels']]
        for selector in selectors:
            print(resolve(selector)['display_name'])
            for entry in channel_playlists(selector, catalog):
                print(f"  {entry['id']}\t{entry['title']}")
    else:
        raise SystemExit('usage: python scripts/playlists.py list [channel] | export [output.md]')
