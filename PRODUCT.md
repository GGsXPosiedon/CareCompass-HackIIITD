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

Family-workspace refinement: remove Ask CareCompass and Find care from its navigation, and remove the Home chat section. Preserve the approved dark conversational landing page and its fonts; the light family workspace remains secondary.

CareCompass name and original compass SVG. User requests a minimalistic interface, references Urban Company and Uber for booking clarity, and Roojh for secondary patient workflows. Latest explicit direction (24 October 2026): build directly from the supplied ChatGPT screenshot with a dark, spacious chat interface and Claude-like typography. This specific reference replaces the earlier unselected visual-concept round and the teal-and-white landing direction. Use open-source Lora serif headings and locally bundled Instrument Sans interface text; preserve the lighter family workspace as a secondary surface. The main experience is the exact fever → follow-ups → recommendation → caregiver → time → demo confirmation → My bookings journey, rather than a health dashboard.

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
