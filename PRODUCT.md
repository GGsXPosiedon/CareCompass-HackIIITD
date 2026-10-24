# CareCompass

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Patients and family caregivers seeking suitable care, including elderly and low-literacy users. The landing page is explicitly a patient introduction whose primary action starts finding care (user confirmed).

## Product Purpose

Understand a text or voice care request in English, Hindi or Hinglish, ask targeted follow-ups, explain a care type and urgency, and connect the user with an appropriate caregiver. Emergency responses bypass matching and booking.

## Operating Context

Hack IIITD frontend project. The source problem_statement.md is the supplied challenge. The user's team role is frontend development. The existing React/TypeScript/Vite application includes a Roojh-inspired family health workspace and the original care-navigation flow.

## Capabilities and Constraints

The runnable app uses synthetic cases, caregiver profiles, records, vitals, reminders and bookings. It supports family profiles, a local briefcase, compiled health summaries, readings, reminder history, scripted conversations, local consent previews, ABHA and hospital-request previews. Actual backend triage, real appointments, identity verification, OCR, clinical review, secure sharing, government integration and live AI are not connected. It must not diagnose, prescribe, invent affiliations, claim medical accuracy or collect real patient information. The optional care API adapter is separate from the demo health workspace.

## Brand Commitments

Theme contract: provide one dark/light toggle in the main header. The selected mode applies to the entire app, including Find care, My bookings, Briefcase, health services and dialogs. Do not give individual sections independent dark/light themes. Keep the approved typography and layout; dark is the initial mode.

Navigation contract: keep the approved dark care landing and fonts. Main navigation has exactly Find care, My bookings and Briefcase. Briefcase contains Home, Records, Health summary and Labs. Explore health services belongs inside My bookings. The family-workspace page, family profiles, ABHA preview, Messages & updates, Workspace settings and Care appointments have been removed. There is no separate workspace sidebar, profile-management control or Home chat.

CareCompass name and original compass SVG. User requests a minimalistic interface, references Urban Company and Uber for booking clarity, and Roojh for secondary patient workflows. Latest explicit direction (24 October 2026): build directly from the supplied ChatGPT screenshot with a dark, spacious chat interface and Claude-like typography. This specific reference replaces the earlier unselected visual-concept round and the teal-and-white landing direction. Use open-source Lora serif headings and locally bundled Instrument Sans interface text; retain the lighter record/service styling within Briefcase and health services. The main experience is the exact fever → follow-ups → recommendation → caregiver → time → demo confirmation → My bookings journey, rather than a health dashboard.

## Evidence on Hand

Working application code and synthetic datasets in frontend/src; original brief in problem_statement.md; supplied patient workflow references documented in README.md. No real patient results, testimonials, professional endorsements, compliance certifications, commercial pricing or user-volume evidence exists.

## Product Principles

- Explain the next action in plain language.
- Keep emergency escalation above the booking workflow.
- Show the product working with honest synthetic examples.
- Keep each family member's information separate.
- Treat incomplete integrations as labelled previews.

## Accessibility & Inclusion

Mobile-first flows, readable contrast, large controls, keyboard focus, labelled inputs, Hindi font support, optional speech with typing fallback, and reduced-motion support.
