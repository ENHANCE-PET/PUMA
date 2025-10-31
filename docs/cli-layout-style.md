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
