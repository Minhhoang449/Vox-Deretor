# Editorial review loop for documentary narration

Use this loop for new narration and explicitly requested narration revisions. It does not reopen approved legacy narration by default. The infographic's labels are adapted as review stages; they are not executable slash commands or permission to change the channel DNA.

## Sequence

Use the six manual questions and draft handoff in [script-packaging-coordination.md](script-packaging-coordination.md). Run `python scripts/draft_review_checks.py <narration.md>` for exact-repeat diagnostics and optional evidence-mapping checks; manually check paraphrase repetition, hook truth, changed scene roles, source strength and all essential claims. Never move all caveats to one paragraph or promote an interpretation to fact after first attribution. Report blockers with actual lines and repairs. A clean diagnostic result is not approval.

Use the six manual questions and draft handoff in [script-packaging-coordination.md](script-packaging-coordination.md). Run `python scripts/draft_review_checks.py <narration.md>` for exact-repeat diagnostics and optional evidence-mapping checks; manually check paraphrase repetition, hook truth, changed scene roles, source strength and all essential claims. Never move all caveats to one paragraph or promote an interpretation to fact after first attribution. Report blockers with actual lines and repairs. A clean diagnostic result is not approval.

1. **Research and lock the promise.** Resolve the live channel, audience language and market. Build the topic brief, source dossier, claim ledger and story card. Confirm that the evidence can support the central answer and each essential causal link before drafting.
2. **Write continuous narration.** Follow the live channel's writing contract and narrative grammar. Keep source administration, editorial directions and review notes out of spoken copy. Preserve material dates, scope and uncertainty at the affected claim.
3. **Red-pen pass.** Review the actual text and quote each consequential weak passage. Flag unsupported or overbroad claims, unclear references, repeated conclusions, passages that add no new understanding, generic explanation that does not earn its place in this episode, stiff or unidiomatic speech, false suspense, and an opening or ending that misses the promise. State the defect and the evidence or change needed; do not merely label a line "weak."
4. **Fact-check the proposed edits.** Check every factual change against the claim ledger and primary or authoritative evidence. Recheck numbers, names, dates, definitions, jurisdiction, causal language and uncertainty. A smoother sentence is not evidence, and an AI disclaimer cannot repair an unsupported claim. Update the dossier/ledger when research changes.
5. **Channel-voice and naturalness pass.** Read the revised speech aloud or review a native-language reading when available. Use the live profile's narration direction, avoid list and suitable benchmark evidence. Remove formulaic transitions, redundant restatements, vague filler, inflated certainty and generic stock phrasing when they occur. Keep specific detail, natural variation, useful technical language and necessary qualifications. Do not imitate a reference creator line by line.
6. **Pattern and wording check.** Check for recurring structures that weaken this actual draft, such as repeated "but here's the twist" pivots, unsupported binaries, repeated three-part lists, stacked rhetorical questions, or conclusions that restate the same payoff. Treat them as contextual flags, not automatic errors. Do not use a universal banned-word list: a term may be accurate or idiomatic in one channel, topic or language and wrong in another. The channel's explicit avoid list and factual terminology take precedence.
7. **Second red-pen pass.** Review the complete revised version, not just changed lines. Confirm that edits did not introduce new claims, remove needed qualifications, break transitions, or leave adjacent passages with the same contribution. Quote any remaining blocker and revise it.
8. **Separate story and retention reviews.** On the exact current speech, record its source and normalized SHA-256. Run story edit `/16` and retention audit `/10` as distinct passes; quote the opening, consequential middle, ending and longest stalled passage. Verify claimed cuts against the text. A missing essential answer, unsupported core causality, fabricated testimony or broken central promise blocks approval regardless of score. Scores are editorial judgments, not performance measurements.
9. **Handoff only after review.** Present the revised narration for user approval. Do not create beats or start production from a polish request, a self-review score or an unapproved draft. After approval, follow narration-review.md and the local production gates.

## Keep the draft natural

Apply the spoken-language pass in [documentary writing framework](documentary-writing-framework.md). Record actual read-aloud/listening findings when performed: first-hearing clarity, referents, terms, breathing and rhythm. A silent text review must not be described as listening; the later approved native-speed audio review remains required.

Channel progression paths diagnose the explanation; they are not compulsory chapters. Keep question maps, source administration and review labels in notes. Choose spoken order from the evidence and viewer's question. Let supported tasks, objects, findings and changes carry connected prose. Do not verbalize the checklist, manufacture a turn or add material merely to reach the runtime target.

## Exit condition

The loop is complete when the factual blockers are resolved, the live channel's grammar and voice are supported by actual passages, the red-pen pass has no unresolved high-risk issue, and the separate story/retention reviews are recorded against the same text version. This means editorially ready for user review; it does not mean proven to retain viewers. If an essential link remains unsupported, research it further or narrow the promise within the agreed subject.

## Review record

Record the speech path/version and normalized SHA-256; channel/topic; exact weak lines and diagnoses; research or wording changes; fact-check results and any open uncertainty; language/benchmark limits; remaining blockers; story and retention scores; reviewer identity/independence; and whether review was text-only, listened, or checked against finished visuals. Keep audience analytics separate and use them only after publication.
