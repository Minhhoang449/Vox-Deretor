# Channel voices and narration delivery

Use the bound channel's clone reference and language from `config/channels.json`. The active routes are local VieNeu for Vietnamese and OmniVoice for the other configured languages.

```text
python scripts/channels.py voices
python scripts/channels.py show <channel-id>
```

`voices` lists the configured clone sources. `show` returns the current channel profile and shared `narration_dna` for authoring. Bind a new episode through `channels.py bind` as described in `local-pipeline.md`; an existing episode's approved voice configuration remains its production input.

## Writing versus audio delivery

- Write with `scripting-dna.md` and the selected channel's current `narration_direction`: food origins, inventions, past daily life, social conventions, Japanese human history or Vietnamese human geography. Let the supported task, finding and human consequence carry curiosity and tone. No universal deadpan or satire requirement applies.
- These are editorial instructions. The local cloned-voice runners use reference audio/transcript; they do not send `narration_direction` as a TTS style instruction. Putting “documentary narrator” or another persona into `voice.instruct` does not implement the active voice direction.
- Let wording and the researched situation carry the tone. Use natural rhythm, selective emphasis and useful pauses; keep sensitive scenes sober.
- Preserve the selected voice and approved synthesis/quality settings. Measure narration before visuals and listen to the resulting audio before claiming it sounds natural.

## Synthesis defaults — 2026-10-12

`config/pipeline.json` is the runtime source of truth:

| Engine | Synthesis speed | Inserted silence after a full stop |
|---|---|---|
| OmniVoice | 0.9 | 0.8 seconds |
| VieNeu v3 Turbo | 1.0 (native output) | 0.8 seconds |

OmniVoice retains `num_step: 32`. The shared runner uses `default_speed` and `pause_after_period_seconds` from the relevant engine block. Existing `tts_speed` and `tts_pause_after_period_seconds` in an episode remain explicit overrides. VieNeu v3 Turbo has no native speed control: 1.0 uses the unchanged generated speech, and another requested speed stops with an explanation rather than being silently ignored or applied with time-stretch.

Both routes synthesize full-stop-delimited sentences and join them with a sample-counted silence segment, including after a final full stop. Western `.` and Japanese `。` / full-width `．` are supported; decimals, common titles/initials and ellipses are not treated as sentence boundaries. Other punctuation keeps the engine's natural rhythm. Negligible model silence at joined edges is trimmed with a short guard around speech; the configured 0.8 seconds describes the inserted segment, and natural speech release may add a small amount.

Here and in the production guides, “native-speed timing” means measuring generated narration at the approved engine settings, including these pauses, without post-generation tempo changes or runtime padding. If timing misses the agreed runtime, revise and reapprove narration. As of 2026-10-16 all six active channels have separate male clones from the user-supplied samples in D:\Coder\Voice. Profiles are saved in D:\Coder\Voice\profiles\2026-10-16: Vietnamese uses VieNeu v3 Turbo; the four English voices and Japanese use OmniVoice. config/channel-voice-overrides.json preserves these routes if the relaunch generator is used again. The former female Vietnamese calibration is retired; use only the matching provisional male-voice measurement described below. Clone files have been created, but long-form listening quality is not established merely by enrollment.

The current male clones now have a provisional single-episode calibration in the live profiles, measured on 2026-10-17. Use it only when voice, language and synthesis settings match; it does not establish listening quality or guarantee another script's runtime.

The effective speed, pause and pause implementation are included in the audio cache fingerprint. Under narration-review.md, TTS first checks the recorded approved speech, then reuses matching audio or regenerates mismatched audio and updates beat durations. New caches include speech and WAV content receipts, and a listening copy is exported automatically before images. Changing config alone does not edit an existing episode. Recheck visual coverage and caption alignment against the new WAV before rebuilding a final video.

The former Atlas voice roster, `leo` default, and seed-audio persona recipes have been removed from this guide. Atlas compatibility code remains for legacy projects; it is not the voice-selection or writing path for new episodes.
