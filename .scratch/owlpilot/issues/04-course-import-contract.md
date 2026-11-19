# Define the first course-material import contract

Type: grilling
Labels: wayfinder:grilling
Status: resolved
Assignee: lead
Blocked by: none
Parent: [OwlPilot — Personal academic co-pilot](../map.md)

## Question

For the files-first release, which user-supplied material formats and initial course scope must be supported, and which extracted facts require student confirmation before they affect priorities or review guides?

## Context

The user chose files before live university access. No real academic materials have been supplied yet. The existing prototype contains fictional courses, historical demo dates, grades, and inconsistent date/day examples. These must never be promoted to personal facts. Determine the minimum useful import flow, explicit demo/real separation, source attribution, and handling of ambiguous or missing deadlines through a live user exchange.

## Comments

User confirmed starting with one course and adding more if time permits, and asked whether the application should work for any course. Answer: the design should be subject-agnostic and use course identifiers/source-linked records rather than hardcoded MATH/CS/HIST-specific branches. One course is the demo/test scope, not an architectural single-course limit. This does not establish that every document format, diagram, equation, grading system, or generated answer is supported or accurate. At that point the combined recommendation's remaining choices (formats, source confirmation, and sample fixture) had not been explicitly accepted.

## Answer

In the subsequent confirmation the user selected “Yes, proceed with this plan” for:

- One course for the demo/test flow, with a subject-independent design rather than hardcoded course logic; more courses are stretch scope.
- Text-based PDF, Markdown, plain text, and pasted text input.
- Defer scanned-PDF OCR. Do not silently treat failed extraction as empty course material.
- Show source-linked extracted topics and deadlines for student confirmation before activation.
- Keep clearly labeled sample-course data separate from real records. No fictional prototype facts are imported into the student's course by default.

Missing or ambiguous facts remain unresolved until confirmed; supported document types do not imply guaranteed extraction of every table, diagram, or mathematical expression. The exact size limits, extraction implementation, and verification cases will be stated in the final proposed specification, not assumed to be user-approved yet.
