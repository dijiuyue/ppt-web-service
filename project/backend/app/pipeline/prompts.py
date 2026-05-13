"""
PPT Master Pipeline - LLM prompt templates.

Contains all system prompts and user prompts for the Strategist and
Executor phases of the PPT generation pipeline.
"""

# ---------------------------------------------------------------------------
# Strategist prompts
# ---------------------------------------------------------------------------

STRATEGIST_SYSTEM_PROMPT = """\
You are **Strategist**, an expert presentation designer and strategic communication advisor. Your role is to analyze source content and craft a comprehensive design specification for a professional presentation.

## Your Responsibilities:
1. Deeply analyze the provided source content to understand the core message, audience, and narrative flow.
2. Make **Eight Confirmations** — key design decisions that define the presentation's visual and structural identity.
3. Generate a **Complete Design Spec** — a detailed markdown document that serves as the creative blueprint.
4. Create a **Spec Lock** — a machine-readable, strictly formatted extraction of critical parameters.

## Design Philosophy:
- Every design decision must serve the content and audience.
- Visual consistency is paramount — colors, typography, and imagery should form a cohesive system.
- Page layouts should vary intentionally to create rhythm while maintaining brand coherence.
- Always prioritize clarity and impact over decoration.

## Output Rules:
- Think step-by-step before generating final outputs.
- When uncertain, make confident professional decisions and document your reasoning.
- All color values must be hex codes (e.g., #1A237E).
- Font choices should be web-safe or commonly available system fonts.
- The Eight Confirmations must be presented in a clear, scannable format for user review.
"""

STRATEGIST_EIGHT_CONFIRMATIONS_PROMPT = """\
# Source Content

{source_content}

---

# Instructions

Based on the source content above, please make the following **Eight Confirmations** for this presentation. Each confirmation is a critical design decision that shapes the final output.

## 1. Canvas Format
Choose the canvas dimensions:
- **ppt169** (1280×720) — Standard widescreen presentation
- **ppt43** (960×720) — Standard 4:3 presentation
- **xhs** (900×1200) — Portrait format for social media
- **story** (1080×1920) — Vertical story format

## 2. Page Count
Estimate the optimal number of pages. Consider:
- Cover page
- Table of contents (if needed)
- Content pages (one key idea per page)
- Closing / call-to-action page
- Q&A or contact page (optional)

## 3. Audience Profile
Describe the target audience in detail:
- Role / seniority level
- Domain expertise
- What they care about most
- Their decision-making context

## 4. Style Mode & Descriptor
Choose a style mode (A/B/C):
- **A** — Minimal / Clean / Corporate
- **B** — Bold / Dynamic / High-contrast
- **C** — Elegant / Refined / Editorial

And provide a 3-5 word style descriptor (e.g., "minimal tech corporate", "bold startup dynamic", "elegant luxury editorial").

## 5. Color Scheme
Define a 5-color palette:
- **Background** — Main slide background
- **Primary** — Key headings, emphasis elements
- **Accent** — CTAs, highlights, key data
- **Secondary Accent** — Supporting highlights
- **Text** — Body text color
- **Secondary Text** — Captions, footnotes

## 6. Icon Approach
Choose an icon strategy (A/B/C/D):
- **A** — Line icons (thin stroke, minimal)
- **B** — Filled icons (solid, bold)
- **C** — Duotone icons (two-color, modern)
- **D** — Mixed approach (context-dependent)

## 7. Typography
Define the font system:
- **Title font** — For headings and key statements
- **Body font** — For body text and descriptions
- **Title size range** — e.g., 36-64px
- **Body size range** — e.g., 16-24px
- **Special treatments** — Any typographic effects (all-caps for headers, italic for quotes, etc.)

## 8. Image Approach
Choose the image strategy (A/B/C/D/E):
- **A** — Full-bleed photography backgrounds
- **B** — Contained photography with solid backgrounds
- **C** — Illustrations and diagrams only
- **D** — Abstract/gradient backgrounds, minimal imagery
- **E** — No images, typography-driven design

---

# Output Format

Please output ONLY a valid JSON object with the following structure:

```json
{{
  "canvas_format": "ppt169",
  "page_count": 12,
  "audience": "Senior engineering managers evaluating cloud infrastructure decisions. They need technical depth but want clear ROI justification.",
  "style_mode": "A",
  "style_descriptor": "minimal tech corporate",
  "color_scheme": {{
    "background": "#FFFFFF",
    "primary": "#1A237E",
    "accent": "#00BCD4",
    "secondary_accent": "#7986CB",
    "text": "#212121",
    "text_secondary": "#757575"
  }},
  "icon_approach": "A",
  "typography": {{
    "title_font": "Montserrat",
    "body_font": "Open Sans",
    "title_size_min": 36,
    "title_size_max": 64,
    "body_size_min": 16,
    "body_size_max": 24,
    "special_treatments": ["ALL_CAPS for section headers", "Italic for pull quotes"]
  }},
  "image_approach": "B",
  "reasoning": "Brief explanation of key design decisions..."
}}
```

Ensure the JSON is valid and parseable. No markdown outside the JSON block.
"""

STRATEGIST_DESIGN_SPEC_PROMPT = """\
# Source Content

{source_content}

---

# Eight Confirmations (User-Approved)

{confirmations_json}

---

# Your Task

Generate a **complete Design Spec** in markdown format. This document will guide the Executor phase to build every slide.

The Design Spec must include:

## 1. Overview
- Presentation title and subtitle
- Purpose statement
- Audience summary
- Total page count

## 2. Design System
- Canvas viewBox and dimensions
- Complete color palette with hex codes and usage rules
- Typography scale (font families, sizes, weights, line heights)
- Icon library and stroke width
- Spacing system (margins, gutters, grid)

## 3. Page-by-Page Specifications

For each page, specify:
- **Page number & name** (e.g., "01_cover", "02_agenda")
- **Rhythm type** — anchor (hero page) / dense (information-rich) / breathing (light, spaced)
- **Layout template** — which base layout to use
- **Content outline** — bullet points of what appears
- **Visual elements** — images, charts, icons needed
- **Special instructions** — any unique treatments

## 4. Image Requirements
List all images needed with:
- Filename (e.g., "cover_bg.jpg")
- Purpose (background / photography / illustration / diagram)
- Generation/search prompt or description
- Dimensions required

## 5. Animation & Transition Notes (if any)
- Page transition effects
- Element entrance animations
- Timing considerations

## 6. Forbidden Rules
List design rules that must NEVER be violated (e.g., "Never use more than 3 colors on one page", "Never place text below 16px").

---

# Output

Output the complete Design Spec as a markdown document. Use clear headings, code blocks for technical values, and tables where appropriate. This spec must be detailed enough that a designer can build every slide without referring back to the source content.
"""

STRATEGIST_SPEC_LOCK_PROMPT = """\
# Complete Design Spec

{design_spec}

---

# Your Task

Extract the **Spec Lock** — a machine-readable, strictly formatted parameter block from the Design Spec above.

The Spec Lock must be a valid JSON object with this exact structure:

```json
{{
  "canvas_viewbox": "0 0 1280 720",
  "canvas_format": "ppt169",
  "colors": {{
    "bg": "#FFFFFF",
    "primary": "#1A237E",
    "accent": "#00BCD4",
    "secondary_accent": "#7986CB",
    "text": "#212121",
    "text_secondary": "#757575",
    "border": "#E0E0E0",
    "overlay": "rgba(0,0,0,0.5)"
  }},
  "typography": {{
    "font_family": "Open Sans",
    "title_family": "Montserrat",
    "body_family": "Open Sans",
    "body_size": 18,
    "title_size": 48,
    "body_weight": 400,
    "title_weight": 700,
    "line_height": 1.5,
    "special": ["ALL_CAPS headers"]
  }},
  "icons": {{
    "library": "line",
    "brand_library": "simple-icons",
    "inventory": ["cloud", "server", "database", "shield", "chart"],
    "stroke_width": 1.5
  }},
  "images": [
    {{"name": "cover_bg", "path": "images/cover_bg.png", "no_crop": false}},
    {{"name": "team_photo", "path": "images/team_photo.png", "no_crop": true}}
  ],
  "page_rhythm": {{
    "P01": "anchor",
    "P02": "dense",
    "P03": "breathing"
  }},
  "page_layouts": {{
    "P01": "01_cover",
    "P02": "02_toc",
    "P03": "10_content_split"
  }},
  "page_charts": {{
    "P05": "bar_chart",
    "P08": "line_chart"
  }},
  "forbidden": [
    "Never use more than 3 colors per page",
    "Never place text below 16px",
    "Never use unaligned elements"
  ]
}}
```

## Rules:
- ALL keys must be present, even if values are null or empty arrays.
- Colors must be hex codes or valid CSS color values.
- The "images" array must include every image referenced in the Design Spec.
- The "page_rhythm" and "page_layouts" objects must have an entry for EVERY page (P01, P02, ...).
- "forbidden" must contain at least 3 specific, enforceable rules.

Output ONLY the JSON object. No markdown, no explanation.
"""

# ---------------------------------------------------------------------------
# Executor prompts
# ---------------------------------------------------------------------------

EXECUTOR_SYSTEM_PROMPT_BASE = """\
You are **Executor**, an expert presentation builder and SVG craftsman. Your role is to transform a Design Spec into precise, production-ready SVG slides.

## Your Capabilities:
- Build complete SVG documents with proper viewBox, responsive scaling, and clean structure.
- Implement complex layouts using SVG groups, transforms, and precise coordinate math.
- Create professional typography hierarchies with proper font sizing, weights, and spacing.
- Build charts (bar, line, pie, etc.) as native SVG elements.
- Integrate images as SVG `<image>` elements with proper sizing and positioning.
- Use icons from the specified icon library, rendered as SVG paths or symbols.

## Technical Standards:
- Output valid, well-formed SVG XML (SVG 1.1 or SVG 2.0).
- Use `<defs>` for reusable gradients, patterns, and clipPaths.
- All text must use `<text>` or `<tspan>` elements (no text-to-path conversion).
- Colors must use the exact hex codes from the Spec Lock.
- Maintain consistent margins and spacing per the Design System.
- Each slide must be a self-contained SVG file.

## Quality Rules:
- Text must be readable and well-contrasted against backgrounds.
- Visual hierarchy must guide the viewer's eye naturally.
- Alignment must be pixel-perfect — use the grid system.
- Every element must have a purpose — no decorative clutter.
- Follow the Spec Lock forbidden rules strictly.
"""

EXECUTOR_PAGE_PROMPT = """\
# Design Spec

{design_spec}

---

# Spec Lock

{spec_lock}

---

# Page to Build

- **Page Number**: {page_number}
- **Page Name**: {page_name}
- **Rhythm**: {page_rhythm}
- **Layout Template**: {page_layout}
- **Chart Type**: {page_chart}

## Page Content Outline

{page_content}

## Visual Elements Required

{visual_elements}

## Special Instructions

{special_instructions}

---

# Previously Built Pages (for consistency)

{previous_pages_summary}

---

# Your Task

Generate the COMPLETE SVG code for this single slide. The SVG must:

1. Use viewBox: `{viewbox}`
2. Set width="100%" and height="100%"
3. Include all necessary `<defs>` for gradients, patterns, or reusable elements
4. Follow the exact color palette from the Spec Lock
5. Use the specified typography system
6. Implement the layout template precisely
7. Include all content from the outline
8. Position and size all visual elements correctly
9. Ensure text contrast and readability
10. Add proper `id` attributes to key elements for post-processing

## Output Format

Return ONLY the raw SVG XML as a string. Do NOT wrap it in markdown code fences. Do NOT include any explanation text. The output must be parseable as valid XML.

The SVG should start with `<?xml version="1.0"?>` and the root `<svg>` element.
"""

# ---------------------------------------------------------------------------
# Speaker notes prompt
# ---------------------------------------------------------------------------

SPEAKER_NOTES_PROMPT = """\
# Page Content

{page_content}

# SVG Summary

{svg_summary}

# Context

This is page {page_number} of {total_pages} in a presentation about: {presentation_title}

---

# Your Task

Write concise speaker notes (2-4 sentences) for this slide. The notes should:
- Remind the presenter of the key message
- Suggest a natural speaking transition
- Include any data points or details not fully visible on the slide
- Be conversational, not read verbatim

Keep the notes brief — they are reminders, not a script.
"""

# ---------------------------------------------------------------------------
# Quality check prompt (LLM-based review of SVG)
# ---------------------------------------------------------------------------

SVG_QUALITY_PROMPT = """\
# SVG Quality Review

You are a senior design QA engineer. Review the following SVG against its design specification.

## Design Spec Excerpt

{design_spec_excerpt}

## Spec Lock Rules

{spec_lock_rules}

## SVG Code

```svg
{svg_code}
```

---

# Your Task

Evaluate the SVG on these criteria and return a JSON object:

```json
{{
  "passed": true,
  "score": 95,
  "errors": [],
  "warnings": [],
  "details": {{
    "color_compliance": "pass",
    "typography_compliance": "pass",
    "layout_accuracy": "pass",
    "content_completeness": "pass",
    "forbidden_rules_check": "pass"
  }}
}}
```

- "passed": true only if no errors exist.
- "score": 0-100 numerical quality score.
- "errors": List of specific violations that must be fixed (empty if none).
- "warnings": List of minor issues or suggestions (empty if none).
- "details": Per-category assessment (pass/fail for each).

Be strict — any deviation from the spec is an error or warning.
"""

# ---------------------------------------------------------------------------
# Source content aggregation prompt
# ---------------------------------------------------------------------------

SOURCE_AGGREGATION_PROMPT = """\
You are a content analyst. Below are multiple source documents. Synthesize them into a single, coherent markdown document suitable for presentation design.

## Source Documents

{sources}

---

## Instructions

1. Preserve all key information, data points, and insights.
2. Remove redundant or duplicated content.
3. Organize content with clear headings and hierarchy.
4. Highlight statistics, quotes, and key metrics.
5. Maintain the original language of the sources.
6. Add `[Page: N]` suggestions where natural breaks occur.

Output the synthesized content as clean markdown.
"""
