# Speaker-attribution source assets

`tools/prepare_assets.ps1` downloads these two pinned files to this directory at developer-build time:

- `Clear-Aligned-Projections.tsv`
- `character_detail.semantic_data.tsv`
- `LICENSE.md` and generated `ATTRIBUTION.md`

Their repository commit and Git blob checksums are pinned in the PowerShell script. The data are licensed CC BY 4.0 and include FCBH/Glyssen character-detail data under MIT; preserve both notices. Source: https://github.com/Clear-Bible/speaker-quotations/.

**Important limitation:** this dataset is not KJV-specific. Its verse-level quotations/speaker suggestions come from alignment data across translations and are only a provisional review seed. It is not an authoritative KJV speaker map. Ambiguities, alternate speakers, cross-chapter quotations and multiple dialogue segments require review. The finished speaker editor and KJV-specific manual override process are not yet implemented.
