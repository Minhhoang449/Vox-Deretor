"""Render live editorial packaging guidance without generating episode claims."""


def packaging_guide(channel_name, language, rules):
    lines = [
        f"# Title and thumbnail direction — {channel_name}", "",
        f"Language: {language} | Revision: {rules.get('revision', 'shared-only')}", "",
        "These are editorial angles and optional starting patterns, not fixed title formulas, visual branding templates or evidence of performance.", "",
        "Choose the title from this channel's lens and the episode evidence, not by matching a shared How/Why pattern. Food titles should reveal the food practice; tool titles the material or practical change; daily-life titles the lived task; social-rule titles the convention and its consequence. Japanese and Vietnamese wording follows its own local voice and channel lens.", "",
    ]
    for title, key in [
        ('Viewer question', 'viewer_question'),
        ('Title direction', 'title_direction'),
        ('Thumbnail direction', 'thumbnail_direction'),
        ('Role of thumbnail text', 'text_role'),
        ('Opening promise', 'opening_contract'),
    ]:
        if rules.get(key):
            lines.extend([f'## {title}', '', rules[key], ''])
    for title, key in [('Optional title starting points', 'title_patterns'),
                       ('Thumbnail concepts to choose from', 'thumbnail_approaches'),
                       ('Avoid', 'avoid')]:
        if rules.get(key):
            lines.extend([f'## {title}', ''])
            lines.extend('- '+item for item in rules[key])
            lines.append('')
    lines.extend([
        '## Episode review', '',
        'Research current examples in the target language after story lock. Name the actual subject, scope and supported claim. The thumbnail supplies one visible relationship; the title supplies the useful question or specificity; the opening begins delivering it.', '',
        'Choose palette, camera, typography and text position for the episode. New episodes use original Chibi 2D people, objects and explanatory graphics. People clarify supported actions and experiences; no fixed cast ratio. Preserve existing recorded styles. Keep 1280x720 delivery, exact localized text and phone-size readability. Do not copy publisher characters or present illustrations as archival evidence.', '',
        'A draft image prompt or title pattern is not an actual thumbnail review or evidence of clicks/retention. Review generated images and the finished opening; after publication compare watch time, source-specific CTR and retention.', '',
    ])
    metadata = rules.get('metadata_direction') or {}
    if metadata:
        lines.extend(['## Public metadata', '', metadata.get('description_policy', ''), '',
                      metadata.get('tags_policy', ''), metadata.get('hashtags_policy', ''),
                      metadata.get('chapters_policy', ''),
                      'Keep research and claim ledgers internal; do not append them automatically to public descriptions.', ''])
    return '\n'.join(lines)
