# KJV Speaker Attribution Dataset Research — 2026-11-24

## Decision

As of 2026-11-24, the public sources reviewed do **not** provide a complete, validated, freely redistributable KJV-specific map of every direct-speech word/segment to its speaker. Do not describe the current MACULA/FCBH integration as a KJV speaker map, and do not silently convert every quoted span into a character voice.

The product must preserve its multi-speaker-per-verse data model and Needs Review workflow. Reliable full-Bible attribution should be built from KJV text and independently checked, or based on a dataset whose owner explicitly grants the required extraction, offline redistribution and derivative-use rights.

## Candidate review

### 1. Clear Bible — Speaker Quotations

Repository: <https://github.com/Clear-Bible/speaker-quotations>

- Provides quotation and speaker projections associated with ESV, NIV84, NASB95, NASB77, NRSV, CSB, HCSB and LEB, plus New-Testament OpenText-derived projections. It does not list KJV projections.
- The `Clear` projection is a consensus view across the available translation data, not an actual Bible translation.
- Speaker information derives from Faith Comes By Hearing / Glyssen CharacterDetail and CharacterVerse files; word projections use MACULA original-language identifiers, syntactic/subject referent data and alignment material.
- The project describes the release as an initial effort. Its own documentation warns that quotations and editorial punctuation vary by translation; same-name entities may remain ambiguous and many speakers are unnamed.
- Its sources page says the source materials were CC BY 4.0 or CC BY-SA 4.0 at time of use. Any redistribution must preserve the applicable attribution and share-alike obligations and verify the exact upstream component provenance. This is not a blanket license for unrelated Bible text.

**Project use:** retain only as a provisional cross-translation attribution seed. Do not present its verse ranges as verified KJV speech. Map word-level projections to KJV cautiously, preserve alternatives and force ambiguous spans into human review.

### 2. Logos / Lexham Press — Reported Speech Dataset

Product and documentation pages:
- <https://www.logos.com/product/27288/reported-speech-dataset>
- <https://www.logos.com/product/178500/reported-speech-dataset-documentation>

- Publisher documentation advertises approximately 8,000 speeches, speaker identification for dialogue words, thousands of speakers and addressees, and nested/multiple quotations.
- Logos community documentation describes speaker annotations being mapped from original-language resources to supported translation resources through reverse interlinear alignment. Exact KJV coverage and export compatibility for this application were not confirmed.
- The resource is delivered as a Logos digital edition / within Logos features. The public pages reviewed do not provide a raw JSON/CSV download, independent API contract or license allowing extraction and redistribution inside a separate offline Windows application.

**Project use:** strongest commercial licensing lead. Before considering it, request written answers from the publisher about KJV coverage, machine-readable export/API, offline use, derivative works, redistribution inside a packaged app and commercial use. A Logos purchase or subscription by itself must not be treated as permission to redistribute its data.

### 3. Bible Ontology

Repository: <https://github.com/bibleontology/bibleontology>

- The repository publishes a speaker-aware Bible knowledge graph. Its README states that clauses are read from Hebrew and Greek MACULA syntax trees and that speech turns and their speakers are read from those clauses by models and recorded as readings.
- The displayed Bible text is the Berean Standard Bible, not KJV. Its claims graph is not a ready-made KJV word-span annotation file.
- The project reports about 11,500 records and 21,400 claims in its 2026-10-22 snapshot. It explicitly preserves whether a claim comes from the narrator, a character, or a model/editor reading.
- The repository's `LICENSE-DATA` covers the graph/exports under CC BY 4.0, but expressly says the license does not cover upstream works; MACULA-derived data retains MACULA attribution and WordNet-derived data retains WordNet notices.

**Project use:** possible independent cross-check of narrative facts and speaker candidates, not an authoritative KJV segment map. Any derived-data import needs a provenance audit and required MACULA/other notices. Model-read speech labels must remain suggestions, not unquestioned truth.

### 4. Jesus' Words

Data page: <https://jesuswords.me/data/>

- Publishes 371 passage records covering Jesus speaking in Matthew, Mark, Luke and John, with KJV and WEB segment text and a `wj` marker for Jesus' direct speech.
- The page says scripture source translations are public domain, but the compilation/editorial work is CC BY-NC 4.0. It explicitly prohibits selling the dataset, selling access to it or republishing it as a commercial data product.

**Project use:** technically useful as a Gospel-only Jesus speech comparison, but not suitable for inclusion in a product that may be sold or commercially distributed without different written permission. It covers Jesus, not the rest of the cast.

### 5. Theographic Bible Metadata

Project information: <https://viz.bible/bible-data/> and <https://github.com/robertrouse/theographic-bible-metadata>

- Includes KJV (1769) Bible text/reference data and structured people, places, events and verse/entity links. The project describes the KJV text as linked to writers and people/places/events.
- The data is licensed CC BY-SA 4.0, requiring attribution and compliance with the share-alike terms for adapted material.
- The entity-verse links identify who or what is mentioned in a verse; they do not identify which person speaks each word or delimit direct-speech segments.

**Project use:** potential alias/entity-resolution support, not speaker attribution. Its share-alike requirements need to be included in any redistribution assessment.

## Engineering decision and next steps

1. Keep the current FCBH/MACULA seed as a *suggestion source only*. Record the exact source label, reference span, candidate speaker, alternate candidates, source translation and confidence/provenance on every imported suggestion.
2. Do not overwrite an existing manual assignment with a dataset import. Ambiguous labels, unnamed speakers, overlapping quotations and nested quotes stay in Needs Review.
3. Build a KJV-specific adjudication set before trusting automatic assignment. Include narrative dialogue, Psalms, prophetic speech, quoted scripture inside dialogue, Gospel dialogue, epistles, crowds, unnamed speakers, speaker changes inside verses and alternate readings.
4. Evaluate Theographic only for entity/alias enrichment after a file-level license/provenance audit; never infer that a person mentioned in a verse is the speaker.
5. Ask Logos/Lexham Press about export and redistribution rights before considering its proprietary dataset. Do not scrape or bundle protected content.
6. Use model/rule suggestions to reduce review effort, not to fabricate certainty. Store `source`, `source_version`, `source_reference`, `confidence`, `alternates`, `review_status` and a manual-override flag in the attribution layer.

## Source links

- Clear Bible project and data scope: <https://github.com/Clear-Bible/speaker-quotations>
- Clear Bible source/license provenance: <https://github.com/Clear-Bible/speaker-quotations/blob/main/sources.md>
- Logos Reported Speech Dataset: <https://www.logos.com/product/27288/reported-speech-dataset>
- Logos Reported Speech documentation: <https://www.logos.com/product/178500/reported-speech-dataset-documentation>
- Bible Ontology README: <https://github.com/bibleontology/bibleontology>
- Bible Ontology data license and upstream notices: <https://github.com/bibleontology/bibleontology/blob/main/LICENSE-DATA>
- Jesus' Words data, provenance and CC BY-NC terms: <https://jesuswords.me/data/>
- Theographic project and CC BY-SA terms: <https://github.com/robertrouse/theographic-bible-metadata>
- Viz.Bible overview of KJV-linked data: <https://viz.bible/bible-data/>

This is engineering research, not a legal opinion. Verify the license text and upstream provenance at the exact pinned commit before bundling any third-party dataset.
