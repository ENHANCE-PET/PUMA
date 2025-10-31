# PUMA CLI Layout Style Guide

This document captures the current display aesthetic introduced in `pumaz.display.section`. Use it as a reference when styling other QIMP tools (for example, LION) so the command-line experience feels consistent and calm.

## Goals
- Keep clinical output and operational logs easy to scan.
- Reduce visual noise from nested boxes; let whitespace and typography handle hierarchy.
- Highlight actions and status changes without overwhelming the core data.

## Core Principles
- **Headings over panels**: Use bold text and a muted divider instead of wrapping every section in a `Panel`.
- **Panels only for context blocks**: Keep `rich.panel.Panel` for elements that benefit from framing—citations, long-form notes, status warnings, or live progress.
- **Consistent rhythm**: Insert a blank line before each heading and keep spacing uniform between sections.
- **Lean typography**: Reserve bold text for section titles and key labels; keep body copy in the default `PUMAZ_COLORS["text"]`.
- **Accent line**: Follow each heading with a muted horizontal rule to anchor the reader without boxing the whole section.

## Banner Pattern
- Try to call `cfonts.say` first, fall back to `cfonts.render`, then `pyfiglet.figlet_format("speed")`. This keeps the banner consistent even when optional dependencies are missing.
- Print a blank line before and after the banner output so it does not crowd adjacent content.
- Subtitle: use bold secondary colour; tag line: secondary colour; both centered with `Align.center`.
- Adjust `PUMAZ_BANNER_COLORS` if a sibling project needs a different palette, but retain the two-tone gradient for familiarity.

## Citation Panel
- Title uses the `:books:` icon, bold secondary colour, left-aligned.
- Wrap the citation body in a `Panel` to frame the long text; keep padding `(1, 2)` so it feels intentional but not heavy.
- Body copy stays white for maximum contrast; end with a blank `console.print()` to separate the next section.
- Maintain the panel even in the flattened layout—it is a reference block users may copy verbatim.

## Notes and Warnings
- Use a `Panel` titled `:memo:` (or `:warning:` for alerts) with borders from `PUMAZ_CITATION_BORDER_COLOR` so all contextual blocks match.
- Compose the message with muted body text, accent subheadings, and bold warning sentences.
- Use the ` • ` bullet prefix inside panels to list arguments or steps cleanly.
- Log the same message via `logging` for audit trails; keep CLI and logs aligned.

## Progress Displays
- Construct progress bars with `themed_progress` so colour semantics stay consistent (`muted` background, `primary` completion, `info` percentage).
- Allow additional columns (ETA, transfer speed) via `*additional_columns` to encourage reuse rather than re-styling.
- Default `transient=True` so the bar clears when complete unless a caller overrides it.
- If porting to another tool, expose a thin wrapper (e.g., `lionz.display.themed_progress`) so every task shares the same progress aesthetic.

## Colour Theme
- All CLI colours live in `constants.PUMAZ_COLORS`. Treat it as the single source of truth and import from there instead of hard-coding hex values.
- Current intent:
  - `primary` — celebratory/action highlights (completed steps, key banners).
  - `secondary` — headings, subtitles, and other structural text.
  - `muted` / `text` — default body text, accent lines, progress bar backgrounds.
  - `accent` — inline emphasis that should pop without reading as a warning.
  - `info`, `warning`, `error`, `success` — semantic states; keep their meanings consistent across projects.
- Whenever a new tool needs different branding, clone the dictionary and adjust values, but maintain the key names so shared helpers continue to work.
- Prefer hex colours for Rich output; only fall back to ANSI when interacting with non-Rich streams.

| Key        | Hex Code  | Typical Usage                              |
|------------|-----------|--------------------------------------------|
| primary    | `#ff79c6` | celebratory accents, completed steps       |
| secondary  | `#4163ca` | headings, subtitles, structural text       |
| success    | `#34c658` | confirmations, healthy status messages     |
| warning    | `#f0c37b` | gentle alerts, next-step nudges            |
| error      | `#eb7777` | failures, actionable errors                |
| info       | `#2b60dc` | informational callouts, progress text      |
| accent     | `#bd93f9` | inline emphasis inside panels or paragraphs|
| muted/text | `#44475a` | body copy, accent rules, background bars   |
| border     | `#D795BE` | panel borders, subtle separators           |

## Implementation Pattern
Re-use the section helper as the foundation for this style.

```python
def section(title: str, icon: str = ""):
    heading = emoji.emojize(f"{icon} {title}" if icon else title).strip()
    header_text = Text(heading, style=f"bold {constants.PUMAZ_COLORS['secondary']}", justify="left")
    accent_width = max(12, min(console.width - 4, 48))
    accent_line = Text("─" * accent_width, style=constants.PUMAZ_COLORS["muted"])
    console.print()
    console.print(header_text)
    console.print(accent_line)
    console.print()
```

### When porting to another tool
1. Import or copy the helper; adjust the palette if the project uses different brand colours.
2. Replace card-styled headings with `section("Title", ":icon:")`.
3. Review existing panels; keep only those that display persistent context (citation, long notes, warnings, live progress).
4. Test a representative CLI run to ensure spacing reads well on typical terminal widths.

## Dos and Don'ts
- **Do** group related utility info (downloads, standardisation steps) inside one loose block with headings.
- **Do** surface actionable items (copyable commands, toggles) as inline buttons or chips when possible.
- **Do** leave breathing room between heavy data outputs and support text.
- **Don't** stack panels back-to-back unless they represent independent alerts.
- **Don't** mix multiple framing techniques (panel + accent line) in the same section.

## Applying the template quickly
When adapting another CLI:
1. Audit where panels are used today and tag which ones must stay (alerts, help text).
2. Introduce the `section` helper and swap it in.
3. Run the command with sample data, capture a screenshot/log, and tweak accent widths or colours as needed.
4. Capture before/after notes in the repository’s documentation so future updates can follow the same pattern.

By centralising this guide we shorten design discussions and make future CLI refreshes faster to execute. Feel free to update the guide with additional snippets or examples as the look evolves.
