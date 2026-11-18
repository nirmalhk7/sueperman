---
name: "Sueperman"
description: "Consumer Test Lab for evidence-backed purchase review"
colors:
  blue: "#2148c0"
  blue-dark: "#173487"
  yellow: "#f5da57"
  ink: "#18273e"
  muted: "#536074"
  line: "#ccd3db"
  paper: "#f3f5f0"
  white: "#fff"
typography:
  display:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "clamp(48px, 6vw, 80px)"
    fontWeight: 700
    lineHeight: 0.99
    letterSpacing: "-.025em"
  headline:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-.01em"
  title:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.5
rounded:
  label: "3px"
  chip: "4px"
  field: "5px"
  button: "7px"
  notice: "8px"
  panel: "12px"
  workbench: "14px"
spacing:
  "8": "8px"
  "12": "12px"
  "16": "16px"
  "20": "20px"
  "22": "22px"
  "24": "24px"
  "28": "28px"
  "32": "32px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.white}"
    rounded: "{rounded.button}"
    padding: "13px 19px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.blue-dark}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "13px 19px"
    typography: "{typography.label}"
  button-highlight:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "13px 19px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "10px 12px"
  card:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.panel}"
    padding: "28px"
  agent-workbench:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.white}"
    rounded: "{rounded.workbench}"
---

# Design System: Sueperman

## Overview

**Creative North Star: "Consumer Test Lab"**

A cool paper work surface pairs saturated laboratory blue with warm yellow signals. Condensed headings supply a strong, practical voice; precise ruled records and readable supporting text keep purchase evidence central. The receipt-shaped Sueperman mark remains the identity anchor.

Depth comes from contrasting work surfaces and divisions rather than shadows. Role explanations and case decisions use the same blue workbench vocabulary; explicit explanations and provider labels keep the presentation grounded in what the product actually did.

**Key Characteristics:**
- Cool paper, laboratory blue and warm yellow signals.
- Condensed headings with calm sans-serif supporting text.
- Ruled evidence records and flat work surfaces.
- Clear distinction between role explanations and actual execution.

## Colors

### Primary

- **Laboratory Blue** (`colors.blue`): primary actions, role workbench, decision band and result totals. Deep Blue (`colors.blue-dark`) supplies action hover contrast.

### Secondary

- **Signal Yellow** (`colors.yellow`): explanation label, selection highlight and small workbench marks. It is not a success indicator.

### Neutral

- **Paper** (`colors.paper`): page surface. **White** (`colors.white`): evidence cards and selected role tab.
- **Ink** (`colors.ink`): primary content. **Muted** (`colors.muted`): supporting descriptions. **Rule** (`colors.line`): record boundaries.

Status pills additionally use green for verified/review-ready, amber for missing information, red for rejection and purple for simulation. Their literal fills and borders remain component-level state treatments, not a second primary palette. Focus uses a contrasting burnt-orange outline.

## Typography

**Display Font:** self-hosted Barlow Condensed, sans-serif fallback; bold face (700).
**Body Font:** self-hosted DM Sans, sans-serif fallback; regular (400), semibold through bold (600–800).
**Label/Mono Font:** system monospace for identifiers, source hashes and draft text, never display headlines.

The frontmatter records the global heading and body ramp. Heading text balances its wrapping; paragraphs generally stop at (72ch). The landing heading uses (clamp(52px, 5.7vw, 80px)); case headings use (clamp(54px, 6vw, 80px)). Workbench verbs are large condensed type; dense records use (12px), supporting labels use (9–12px). These are contextual sizes rather than a uniform scale ratio.

## Layout

The main container is centered, capped at (1360px), with desktop padding (58px 52px 90px). Header caps at (1440px). The landing work surface uses (1.1fr 1fr) columns and a (64px) gap; cards and evidence boards use equal paired columns. Records use full-width collapsed tables with horizontally scrollable wrappers.

At (1080px), horizontal page padding becomes (32px). At (760px), navigation wraps beneath the brand, main padding becomes (38px 24px 56px), workbench/cards/case boards stack, statistics become two columns and the purchase table keeps a (680px) minimum width inside its scroll wrapper. At (380px), main/header side padding becomes (18px). Mobile panels and cards use (22px) padding; case-board cells use (25px).

**The Evidence Together Rule.** Keep identifiers, source modes and observed timestamps close to the finding they qualify.

## Elevation & Depth

Blue inspection and decision surfaces, white records, amber challenges and thin borders establish hierarchy. No box shadows appear in the implemented stylesheet. Dashed boundaries distinguish uploads; line divisions preserve record relationships.

**The Flat Workbench Rule.** Separate records with thin rules and changes in surface color; the implemented system uses no box shadows.

## Shapes

Small rectangular labels and restrained rounded surfaces define the system. Use the recorded field/button/notice/panel/workbench radii by role. Tiny circular tab and mode markers are state cues; SVG line drawings illustrate agent roles. Borders are generally (1px). Cards remain rectangular rather than pill-shaped.

## Components

### Buttons

Primary actions use blue with white labels; hover deepens blue. Secondary controls are transparent with an ink label and muted border; hover adds a pale blue surface and blue text/border. The highlight variant combines yellow with an ink label. Default padding and radius are frontmatter tokens. Disabled controls have opacity (.46) and a not-allowed cursor. Interactive focus uses a (3px solid #bc591c) outline offset by (4px).

### Inputs / Fields

White text fields use a muted stroke, field radius, and body typography at (13px). Selects use semibold (12px) type and (9px 28px 9px 10px) padding. File inputs retain native selection controls inside the dashed upload surface. Confirmation checkboxes use blue accent color and (18px) dimensions. Errors are explicit text alerts with pale red backgrounds; do not infer a field-validation system beyond the implemented native constraints.

### Navigation

Inline muted links use (13px) type and (30px) gaps; hover turns blue and underlines. At the mobile breakpoint navigation takes a full row, with (12px) links and (26px) gaps. A skip link becomes visible on focus. Current section links have no separately implemented active treatment.

### Chips

State labels use compact semibold uppercase text, a thin border and chip radius. Written labels identify status alongside the green/amber/red/purple treatments. Provider badges remain plain bordered white labels.

### Cards / Containers

White cards and panels have ruled borders and panel radius. Desktop padding is (28px), narrowing to (22px). Opportunity cards keep their review link below the supporting evidence metadata. Case workbench cells share a single outer boundary; the challenge cell is pale yellow and decision cell blue.

### Agent workbench

The blue explainer is explicitly labeled How it works. Scout, Skeptic and Builder form a tablist: clicking, Left/Right arrows, Home and End change the matching explanation and focus; only the selected tab participates in normal Tab navigation. A white selected tab and filled dot distinguish the active role. SVG role marks, large action verbs and a numeric role index support the explanation without claiming a live run.

Motion follows the inspection workflow. Role selection moves a shared yellow marker over (360ms), draws the tool icon over (600ms), and runs a single (680ms) inspection sweep; role visuals and explanations reveal over (420ms) and (450ms). New purchase rows settle over (300ms), staggered by at most (175ms); case sections reveal over (520ms), staggered by at most (180ms), and verdict labels settle over (400ms). Controls acknowledge press and transition colors over (180ms). A spinner exists only while an action exposes real `aria-busy` state. No autonomous preview loop runs. Reduced motion removes spatial, clipping and stroke animation; selected and pending states remain static, with (100ms) color feedback.

**The Honest State Rule.** Hide historical recorded cases from the public workspace; preserve truthful source and provider labels; color supports a written state rather than replacing it.

## Do's and Don'ts

### Do:
- Do use the self-hosted condensed family for headings and the body family for controls and supporting copy.
- Do keep case finding, challenge, missing information and deterministic decision visibly distinct.
- Do preserve keyboard focus, roving role-tab selection and reduced-motion behavior.

### Don't:
- Don't present the role preview as execution progress.
- Don't use color alone to distinguish review, rejection or simulation.
- Don't hide source modes or imply local approval submits an external claim.
