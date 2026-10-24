---
name: CareCompass
description: A quiet conversational path to the next care step.
colors:
  care-accent: "#dfab8d"
  care-accent-hover: "#efc4a9"
  care-ground: "#20201e"
  care-sidebar: "#181817"
  care-raised: "#2b2b28"
  care-surface: "#272725"
  care-card: "#242422"
  care-summary: "#2a2a27"
  care-ink: "#eeece6"
  care-muted: "#b2b0a8"
  care-border: "#3b3b37"
  care-control: "#57564f"
  composer-border: "#525149"
  composer-focus: "#c8a489"
  action-paper: "#e9e4da"
  action-ink: "#252521"
  action-hover: "#fff9f0"
  choice-ground: "#4a3c30"
  choice-ink: "#ffe0c7"
  choice-border: "#d7a781"
  danger-ink: "#ffd1c6"
  danger-ground: "#452b27"
  family-ground: "#fff"
  family-ink: "#202622"
  family-muted: "#626c65"
  family-surface: "#f4f7f5"
  family-border: "#dfe5df"
  family-control: "#a9b6ac"
  family-accent: "#1b6e66"
  family-accent-deep: "#15584f"
typography:
  display:
    fontFamily: "'Lora', 'Noto Sans Devanagari', serif"
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 1.25
    letterSpacing: "-.04em"
  headline:
    fontFamily: "'Lora', 'Noto Sans Devanagari', serif"
    fontSize: "36px"
    fontWeight: 400
    lineHeight: 1.25
    letterSpacing: "-.035em"
  title:
    fontFamily: "'Instrument Sans', 'Noto Sans Devanagari', sans-serif"
    fontSize: "21px"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "-.025em"
  body:
    fontFamily: "'Instrument Sans', 'Noto Sans Devanagari', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "'Instrument Sans', 'Noto Sans Devanagari', sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  navigation: "8px"
  prompt: "9px"
  action: "10px"
  care-card: "14px"
  family-card: "16px"
  composer: "18px"
  modal: "20px"
  pill: "100px"
  circle: "50%"
spacing:
  compact: "8px"
  control-gap: "10px"
  inline: "12px"
  regular: "16px"
  inset: "20px"
  section: "24px"
  wide: "32px"
components:
  button-primary:
    backgroundColor: "{colors.action-paper}"
    textColor: "{colors.action-ink}"
    rounded: "{rounded.pill}"
    padding: "12px 23px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.care-ink}"
    rounded: "{rounded.pill}"
    padding: "12px 23px"
  button-send:
    backgroundColor: "{colors.care-accent}"
    textColor: "#251e19"
    rounded: "{rounded.circle}"
    height: "44px"
    width: "44px"
  composer:
    backgroundColor: "{colors.care-raised}"
    textColor: "{colors.care-ink}"
    rounded: "{rounded.composer}"
  navigation-active:
    backgroundColor: "{colors.care-raised}"
    textColor: "{colors.care-ink}"
    rounded: "{rounded.navigation}"
    padding: "11px 13px"
  prompt:
    backgroundColor: "transparent"
    textColor: "#d2cfc5"
    rounded: "{rounded.prompt}"
    padding: "9px 15px"
  choice-selected:
    backgroundColor: "{colors.choice-ground}"
    textColor: "{colors.choice-ink}"
    rounded: "{rounded.prompt}"
    padding: "10px 17px"
  care-card:
    backgroundColor: "{colors.care-card}"
    textColor: "{colors.care-ink}"
    rounded: "{rounded.care-card}"
    padding: "23px"
  family-card:
    backgroundColor: "{colors.family-ground}"
    textColor: "{colors.family-ink}"
    rounded: "{rounded.family-card}"
    padding: "24px"
---

# Design System: CareCompass

## Overview

Navigation: the main sidebar contains Find care, My bookings and Briefcase. Briefcase groups Home, Records, Health summary and Labs in an internal wrapping navigation row. Explore health services lives inside My bookings and returns there. The former family-workspace shell and removed account/profile/settings sections are no longer mounted or available.

**Creative North Star: "A quiet conversation toward care"**

CareCompass uses a dark, spacious conversational shell with a warm serif question and restrained sans-serif controls. The approved ChatGPT-like spatial model and Claude-like type character guide the primary experience; Lora is an open-source approximation of that serif character. The original compass mark and CareCompass name remain the identity anchors.

A compact sidebar holds navigation while the canvas gives the current care decision room. Tonal surfaces, visible input labels and brief supporting text keep the experience calm and readable. Briefcase and health services inherit the same selected dark/light theme inside the single app shell.

**Key Characteristics:**

- Warm charcoal surfaces with soft paper-colored text.
- Serif questions paired with clear sans-serif controls.
- A raised composer and restrained terracotta interaction accents.
- Flat cards and visible selected, disabled, loading and error states.
- One dark/light theme across every app surface.

Evidence: `frontend/src/care-shell.css` supplies the primary world and workspace overrides; `frontend/src/styles.css` supplies inherited primitives; `frontend/src/health.css` supplies the light record and service modules. `frontend/src/main.tsx` bundles the fonts and loads those styles in that order. This is a source-grounded record of the reviewed implementation, not a new visual proposal.

## Colors

`frontend/src/themes.css` is the current color authority and loads after the earlier stylesheets. The shell owns a single `theme-dark` or `theme-light` class. All panels, forms, records, service listings, status states and dialogs inherit that mode. Dark is the initial state and the header toggle switches it without remounting the active workflow.

Light tokens: ground `#faf9f6`, sidebar `#f1efe9`, raised/card `#fff`, surface/summary `#f1f0eb`, ink `#292b26`, muted ink `#66665e`, border `#deddd6`, controls `#a6a497`, accent `#875736`. Dark tokens retain the warm charcoal palette below, with control boundaries strengthened to `#858174`.

**One Theme Rule.** Theme is an app-level preference. Briefcase and health services share the current mode with care and bookings; they must not reset to a separate light surface. The original `family-*` token names below are inherited palette references, not a separate theme boundary.

The primary palette is warm charcoal and paper, with terracotta for conversational actions and selection.

### Primary

- **Terracotta:** the send action, focus accent, completed progress marks and selected caregiver outline. The inherited CSS variable named teal resolves to terracotta inside the care shell.
- **Action Paper:** the primary workflow button fill, paired with dark Action Ink. This is the next-step treatment outside the composer.
- **Warm Choice:** selected answers, dates, slots and location choices use a brown fill, pale peach text and a contrasting warm outline.

### Secondary

- **Family Teal:** an inherited palette reference. Active accents resolve through the shared global theme.
- **Emergency Rose:** pale error text on a deep red-brown ground; emergency headings and lists have their own brighter warm treatment. Status colors communicate state rather than decoration.

### Neutral

- **Conversation Ground / Sidebar / Raised:** the canvas, darker sidebar and lighter composer establish the primary tonal layers.
- **Care Card / Summary:** subtly different container tones distinguish actionable content and supporting summaries.
- **Paper Ink / Muted Ink:** primary text and secondary explanations.
- **Care Border / Control:** restrained dividers and stronger input boundaries.
- **Family Ground / Ink / Surface:** white, dark green-black text and pale green-white panels remain scoped to the secondary workspace.

**The One Theme Rule.** Use the shared tokens from themes.css for every section; one app-level class selects the entire palette.

## Typography

**Display Font:** Lora, with Noto Sans Devanagari and serif fallbacks.
**Body Font:** Instrument Sans, with Noto Sans Devanagari and sans-serif fallbacks.

**Character:** Lora lends questions a warm, conversational character. Instrument Sans keeps navigation, care details and choices direct. Locally bundled font weights are Lora regular and Instrument Sans / Noto Sans Devanagari regular, medium and semibold.

### Hierarchy

- **Display:** the centered intake question; the frontmatter records the desktop role. It steps down to 38px at the compact desktop breakpoint and 34px on mobile.
- **Headline:** serif workflow page headings; mobile reduces them to 30px.
- **Title:** medium sans-serif section headings; individual summaries use 20px.
- **Body:** the inherited reading size and line height. Composer text is 17px with a 1.6 line height, reducing to 16px on mobile.
- **Label:** input labels and small contextual controls. Navigation uses 14px; supporting disclosure text uses 11–12px.
- **Family heading:** the secondary workspace retains a sans-serif page heading at 30px, weight 500 and -.035em tracking, with smaller responsive sizes.

**The Question Voice Rule.** Use the serif for primary care questions and workflow page headings; keep controls and detailed supporting information in the sans-serif.

## Layout

The desktop shell uses a sticky, viewport-height sidebar and a flexible canvas. The sidebar is 256px wide, narrowing to 220px at 1100px. The top bar is at least 76px high. Intake content is centered in a maximum 760px column; auto margins and viewport-relative minimum height keep the question, composer and bottom disclosure spacious without inventing empty history.

Workflow pages sit within a maximum 1120px container with 44px horizontal padding, reducing to 28px at 1100px and 20px on mobile. Care and provider columns collapse to one at 1100px; supporting panels cease being sticky there.

At 767px and below, the shell becomes a single column. Navigation becomes a modal drawer of width min(290px, 85vw), with a dimmed backdrop, keyboard containment, Escape dismissal and focus return. The mobile top bar is at least 68px high. A filled composer stacks patient context above its send-action row as needed. Prompt chips wrap.

The frontmatter spacing vocabulary records repeated source values, not an enforced mathematical scale. Keep compact control spacing within generous section spacing.

Briefcase and health services use a maximum 1220px content area inside the main shell, with 40px desktop gutters and 20px mobile gutters. Briefcase has four wrapping internal navigation buttons with 44px minimum height. There is no secondary sidebar, header or mobile bottom navigation. Inherited record, lab and service panels retain their single-column mobile rules.

## Elevation & Depth

Primary surfaces are flat at rest. Depth comes from the darker sidebar, raised composer, borders and tonal card surfaces. The location/help dialog uses a soft overlay shadow, while modal and drawer backdrops dim the surrounding interface. There are no decorative gradients or hard offset shadows in the primary world.

### Shadow Vocabulary

- **Care dialog:** `0 20px 70px #0008`; reserved for the care flow modal.
- **Inherited light dialog:** `0 15px 70px #18251e26`; retained for light contexts.

Buttons transition background and text color over .15s with ease timing in the care shell. The guide chevron rotates over .15s. Loading uses an .8s linear spinner. Global reduced-motion rules remove animation and transitions.

**The Tonal Depth Rule.** Use surface tone and borders for everyday hierarchy; reserve the established ambient shadow for dialogs.

## Shapes

Corners are softly rounded, with rectangular navigation and choice controls, a larger composer curve, and pill-shaped workflow buttons. The empty send control is circular; when text exists it expands into a labelled action with a 10px radius. Care cards use the shared 14px corner, while family blocks keep their inherited 16px corner. Date controls use an 11px corner. These shapes are functional distinctions, not a single radius applied everywhere.

## Components

### Buttons

Quiet, readable and explicit about the next step.

- Workflow primary buttons use Action Paper with dark ink, pill corners, a minimum 48px height and the frontmatter padding. Hover uses Action Hover; pressing shifts the inherited workflow button down 1px.
- Secondary workflow buttons are transparent with a visible #66645b border; hover adds #383831 and a lighter #aaa591 border.
- The composer send control uses Terracotta. It starts as a circular arrow, expands to the named action when input exists, and shows a spinner while checking.
- Disabled workflow buttons use muted #aba99f on #383833 with #494942 borders; the composer send uses its separate #4a4a42 / #b3b0a2 disabled treatment.
- Keyboard focus uses a 3px accent outline with a 4px offset. Mobile voice controls retain an accessible name while the visible text gives way to the microphone icon.

### Chips

Outlined prompt chips are lightly rounded, at least 44px high, and fill the composer when clicked. Hover uses a subtle darker surface and warmer border. Answer and time choices are larger outlined controls with explicit selected fill, ink and border; selection must remain distinguishable from hover.

### Cards / Containers

Caregiver and booking containers share the dark Care Card tone and 14px corners; summaries use the separate Summary tone. Borders carry their edges without cast shadows. A caregiver card has 23px padding on desktop and 18px on mobile; summary panels use 27px, reducing to 20px. Family health blocks retain white surfaces, light borders, 16px corners and 24px padding.

### Inputs / Fields

The composer has a visible label, raised ground, a 1px Composer Border and 18px corners. Focus within changes its border to Composer Focus. Its textarea is transparent, vertically resizable, capped at 240px high and accompanied by patient context, voice input and submit.

Other care text fields use the raised background, Control border and 10px corners. Error copy appears adjacent to the affected flow, with a live alert and described input relationship. Keep labels, language support and state explanations visible.

### Navigation

The sidebar uses muted sans-serif text, 46px minimum navigation rows and 8px corners. Active rows use Raised and Paper Ink; hover uses #252523 and Paper Ink. The outlined New request action has 10px corners. Briefcase is the third main navigation destination; health services is reached from My bookings. Mobile shows the product name and opens the drawer from the top bar.

### Care Progress

Small circular markers, fine connector lines and muted labels show workflow position. Current markers use Paper Ink; completed markers use Terracotta and a check. Keep the progression subordinate to the current question and action.

## Do's and Don'ts

### Do:

- **Do** preserve the One Theme Rule when extending care or family surfaces.
- **Do** pair serif care questions with sans-serif controls and detailed information.
- **Do** use tonal layers and borders for resting surfaces.
- **Do** show distinct focus, selected, disabled, loading and error states.
- **Do** keep Hindi glyph coverage, visible labels and keyboard navigation.
- **Do** retain plain demo disclosures and emergency emphasis.

### Don't:

- **Don't** introduce decorative imagery or gradients into the approved primary conversational world.
- **Don't** turn the intake into a feature-card dashboard or fabricate conversation history.
- **Don't** replace the original compass identity or imply proprietary Claude fonts are bundled.
- **Don't** promote inherited incidental labels or one-off styling into new system rules.
