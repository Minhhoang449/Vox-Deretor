"""Shared editorial execution policy for the six documentary channels.

Base topic/format DNA stays research-led-documentary-v1; this updates how it is
executed, without invalidating or rewriting previously approved production.
"""

import json
from pathlib import Path

EXECUTION_REVISION = "documentary-story-execution-v4"
CONTRACT_REVISION = "channel-dna-execution-v4"
UPDATED_ON = "2026-10-17"

DNA_UPDATES = {
    "execution_revision": EXECUTION_REVISION,
    "execution_updated_on": UPDATED_ON,
    "passage_progression": "Identify what the viewer can now explain, distinguish or predict that was unavailable before this passage, and the evidence or explanatory step that supplies it. A new study, term, qualification or paraphrase of the same answer is not progress by itself. Keep useful general mechanism and orientation, but merge passages whose removal loses no distinct understanding or necessary scope.",
    "promise_evidence_fit": "Choose the episode promise from the evidence available before drafting. Record which observations, process records or bounded results support the essential answer and what remains unknown. Research a missing essential link or narrow the promise within the agreed subject; do not silently change episode identity or invent a demonstration to fill the gap.",
    "situated_mechanism": "Connect essential general explanation to a sourced condition, action, finding or outcome in this episode's place, event or service task. The consequential middle must depend on those particulars. A place/name substitution test diagnoses a generic spine, but does not prohibit general science or require a field measurement in every paragraph.",
    "comparison_scope": "Only when the promise contrasts outcomes, show the actual named or clearly bounded sides, relevant conditions and supported difference. Check comparable definitions, periods and methods before making causal or numerical comparisons. A regional trend or general mechanism cannot stand in for a missing site-specific comparison; labeled illustration explains a rule but cannot prove an observed outcome. A non-comparative question needs no compulsory second case.",
    "concrete_payoff": "Show the supported outcome and its local or everyday consequence; a promise to follow a flow or comparison must be visible in the actual text. Do not fill an evidence gap with invented people, motives or outcomes.",
    "spoken_information_order": "Establish the job or constraint before technical names. Use numbers for a meaningful scale, threshold or difference; retain material date, jurisdiction and definitions at the affected claim rather than narrating an unusable data comparison.",
    "narration_boundary": "Keep access logs, abstract-only reading status, tool limitations and instructions to the author in the dossier/review. Speak consequential uncertainty, scope and assumptions naturally at the claim. Narrate investigative methods when a finding changes the causal explanation; narrow or research an unsupported claim rather than excuse it with a disclaimer.",
    "transition_policy": "Distinguish a sourced causal consequence, an explanatory prerequisite and the next task in the same system. Do not invent surprise, discovery order, crisis, private thoughts or a claim that the first solution caused the next problem.",
    "answer_timing": "The main answer may arrive early or late. Each intervening passage must pay a useful question. Later branches must serve the title/opening promise or a demonstrated consequence; no fixed teaser interval or mandatory new danger.",
    "viewer_guidance": "Use psychology to guide attention and comprehension: align title/thumbnail with the opening; confirm the click and deliver useful, verified progress within roughly the first 30 seconds; map each major passage as active viewer question → sourced evidence or event change → updated understanding → next question or dependency. Pay partial answers when evidence permits; keep no question open merely to delay its answer. Orient at meaningful changes of time, place, task, state or model, and introduce terms/numbers when their purpose is clear. Close the promise once with the supported consequence or limit. This is a writing method, not a retention guarantee or fixed schedule of hooks, chapters or visual interruptions.",
    "curiosity_path": "Before drafting, write the central question and its answerable subquestions. For each major passage, name the evidence that advances or pays one subquestion and the next question that follows from that evidence. If no distinct understanding or necessary scope is lost by deleting a passage, merge or cut it. A missing answer is not a cliffhanger unless the evidence genuinely requires another step.",
    "cognitive_load": "Orient the viewer to the place, time, task or current state before adding a new causal relation. Explain technical terms after their practical role is clear; keep numbers that support scale, threshold or difference. Use a still, map, comparison or cross-section to clarify the same relation as narration. Do not use image changes, pan/zoom, on-screen text or pacing tricks as substitutes for clear explanation.",
    "audience_feedback": "After publication, use actual YouTube Studio retention by video, including the 30-second intro and dips, spikes and top moments. Match each signal to the exact narration and visuals; a spike may reflect interest, sharing or confusion. Compare similar lengths and traffic sources where data allows. Report observed analytics separately from text review and hypotheses; scores do not predict retention.",
    "ending_test": "Close once the supported answer and relevant consequence or uncertainty are clear. A callback is optional and useful only when its meaning has changed; do not re-tour the route or stack several conclusions. A discussion question is optional after the payoff, not a substitute for it.",
    "review_requirement": "Review the title/thumbnail promise against the first image and the actual first 30 seconds; record the useful progress made by that point. Map the major passage question → evidence/change → updated understanding → next dependency/payoff, and identify any stall caused by repetition, cognitive overload, unclear transitions or unrelated branches. Review full actual speech before prior scores; use separate story /16 and retention /10 passes. Record source/SHA-256, quote opening/consequential middle/ending and verify claimed cuts. Criterion 3 earns 2 only when passages produce distinct, connected advances; criterion 6 earns 2 only when sourced episode particulars carry the consequential middle and payoff in this channel's grammar. A generic explanation with local names earns at most 1 for fit. A missing promised comparison or essential answer blocks recommendation regardless of totals; research or narrow the promise, never raise a score to pass. Label same-author and text/audio limits; scores and shorter runtime do not demonstrate audience performance. Only published audience analytics can describe measured retention.",
    "runtime_planning": "Use the live channel's measured voice/language calibration only when voice, settings and counting method match. It is a provisional drafting budget, not a duration guarantee; confirm approved native-speed TTS before images. Do not infer speech duration from shot budgets, pad repetition, stretch audio or override an accepted episode runtime.",
}

EXECUTION_CHECKS = {
    "last-safe-minute": "Make the food's history legible through supported harvesting, selection, processing, preservation, exchange or meal practices. Show what changed in the food or practice and what evidence supports it in a bounded community and period. Do not assume a single inventor, accidental discovery, universal sequence or inevitable spread. Each passage advances the selected food question, not a disaster/response plot.",
    "terra-rewired": "Explain the practical job, material properties and supported making or use of this tool or technology. Distinguish invention, production, adoption and transmission; show the conditions and trade-offs that matter to this particular question. Do not assume one inventor, an inevitable improvement or a compulsory infrastructure journey. A list of inventions is not an explanation of this invention.",
    "battlefield-bearings": "Reconstruct a bounded everyday-life question through a focused task or connected routines, supported objects, spaces, actions and social conditions. Each routine must advance the same question. Explain material variation; do not present one household as everyone's experience or combine incompatible places/periods into one day. A protagonist, crisis, military frame or dawn-to-night checklist is optional, never required.",
    "status-and-systems": "Explain how this social idea, classification, convention or institution acquired meaning, authority or acceptance in dated cases. Show people applying, contesting or changing it where documented. Distinguish recorded formation from later justification; keep alternatives and scope clear. Neither medieval finance nor a single transaction is a compulsory frame.",
    "chikyu-shikumi": "自然な日本語で、遺物・研究結果・観察された行動から何が分かるかを案内する。各段落で新たに説明できること、推論の範囲、次に確かめる証拠を明確にする。専門語や年代は必要性が分かってから導入する。研究上の解釈と直接観察を区別し、音声と母語話者の確認も分けて記録する。",
    "vi-sao-noi-nay": "Theo một cách cư trú, di chuyển, làm việc hoặc sinh sống tại nơi cụ thể; giải thích con người thích nghi với điều kiện địa lý bằng hành động, vật dụng và quan sát có nguồn. Phân biệt ảnh hưởng của địa lý với lựa chọn văn hóa, lịch sử và điều kiện kinh tế khi có liên quan. Không biến tập thành danh sách địa danh, bài giảng hạ tầng hoặc khẳng định địa lý quyết định mọi hành vi.",
}

EVIDENCE_LIMIT = "Record this episode's actual source access, sampled/transcript evidence, coverage and language-review limits. Public metadata does not establish spoken structure; translated captions do not establish original phrasing. Text review is not listening, finished-video QA or measured audience performance. Dated sample weaknesses are provenance, not assumptions about a new episode."


def execution_contract(existing, channel_id):
    contract = dict(existing or {})
    # Live authoring data is authoritative; an empty contract must not revive
    # an older task-only check from this module's compatibility defaults.
    config_path = Path(__file__).resolve().parents[1] / "config/channels.json"
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    live = next((p.get("writing_contract", {}) for p in config["channels"]
                 if p["id"] == channel_id), {})
    # A shared-policy refresh must not roll a later channel-specific contract back.
    contract.setdefault("revision", CONTRACT_REVISION)
    contract.setdefault("policy_updated_on", UPDATED_ON)
    contract.setdefault("execution_check", live.get("execution_check", EXECUTION_CHECKS[channel_id]))
    for key in ("question_design_revision", "opening_task", "progression_test", "question_scope",
                "narration_boundary", "second_person_policy", "topic_selection_reference"):
        if key in live:
            contract.setdefault(key, live[key])
    contract.update(evidence_limit=EVIDENCE_LIMIT,
                    promise_evidence_fit=DNA_UPDATES["promise_evidence_fit"],
                    comparison_scope=DNA_UPDATES["comparison_scope"],
                    viewer_guidance=DNA_UPDATES["viewer_guidance"],
                    curiosity_path=DNA_UPDATES["curiosity_path"],
                    cognitive_load=DNA_UPDATES["cognitive_load"],
                    audience_feedback=DNA_UPDATES["audience_feedback"],
                    review_scoring=DNA_UPDATES["review_requirement"])
    return contract
