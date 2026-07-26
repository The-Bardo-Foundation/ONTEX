# Front-end design conventions

Scope: the whole front end. The **public viewer** — landing page (`/`), trials search
(`/trials`), trial detail (`/trials/:nct_id`), and the public header — carries the
design most deliberately; the **admin dashboard** (`/admin/*`) shares the palette but
keeps its own denser layout.

The goal is that the site reads as something the Osteosarcoma Now Foundation
publishes, not as a generic dashboard template.

## Palette

Defined in [`frontend/tailwind.config.js`](../frontend/tailwind.config.js).

| Token           | Value     | Use it for                                                        |
|-----------------|-----------|-------------------------------------------------------------------|
| `brand-600`     | `#2563a8` | Primary buttons, links, active nav, the filled timeline numeral    |
| `brand-700`     | `#1e518a` | Hover on `brand-600` fills                                         |
| `brand-50`      | `#eaf1fa` | Soft fills — timeline numerals, the `Partial Match` chip           |
| `accent-600`    | `#8a9a3f` | Section eyebrows (the small uppercase labels)                      |
| `accent-700`    | `#7a9a2e` | The one olive stat figure (`Decades`)                              |
| `accent-800`    | `#607623` | `Match` chip text — the darker step exists to clear AA on the tint |
| `accent-50`     | `#f0f5e8` | `Match` chip background                                            |
| `surface`       | `#fbfaf8` | Warm off-white section backgrounds, page background, hover fills   |
| `surface-muted` | `#f2f2f1` | `Not Suitable` chip background                                     |
| `line`          | `#e8e6e6` | Hairline rules, borders, column dividers                           |
| `line-soft`     | `#eeeeee` | Lighter dividers inside lists and tables                           |
| `gray-900`      | `#111827` | Headings — Tailwind's default, already on palette                  |
| `gray-500`      | `#6b7280` | Body copy — Tailwind's default, already on palette                 |

`brand` is a full `50`–`900` ramp on `hsl(212, 64%, L)`, so every shade index that
Tailwind's own `blue` offered has a one-for-one match. `accent` is deliberately
sparse (`50`, `600`, `700`, `800`) — olive is for small type, never large fills.

Two things that are easy to miss:

- **`borderColor.DEFAULT` is overridden to `#e8e6e6`.** A bare `border`, `border-b`,
  or `border-r` would otherwise fall back to Tailwind's cool `gray-200`, which reads
  wrong next to the warm `surface`. You do not need `border-line` on bare borders.
- **`tailwind.config.js` is read once when Vite starts.** After editing the palette
  you must restart `npm run dev`, or the new classes compile to nothing and elements
  like the primary button render as white-on-transparent.

### What stays off-palette

The recruitment-status badges in
[`utils/formatters.ts`](../frontend/src/utils/formatters.ts) keep Tailwind's default
`green` / `yellow` / `red` / `blue` ramps. They map to real ClinicalTrials.gov states
(Recruiting, Active-not-recruiting, Completed, …) and are semantic, not brand
colour — recolouring them to `brand` would lose the distinction they exist to carry.
That is the one intentional `blue-*` left in the codebase.

## Rules

- **Accent eyebrow, then heading.** Sections open with a small uppercase letterspaced
  `accent-600` label (`text-xs font-semibold tracking-[0.18em]`), then the real
  heading in `gray-900`. No coloured heading text.
- **Rules, not cards.** Separate content with hairlines (`border-line`) or a column
  divider. Avoid `rounded-xl` card grids — a page made of floating rounded boxes is
  the main thing that reads as machine-generated.
- **Radius stays small.** `rounded` (4px) or none. `rounded-full` only on the timeline
  numerals.
- **One accent per element.** Buttons are `bg-brand-600`; links are `brand-600` with a
  thin underline. No gradients, no shadows beyond overlays.
- **No emoji as iconography**, and no text glyphs (`▾`, `→`) used as UI chrome.
- **Muted chips.** The three classification labels are soft tints (`accent-50`,
  `brand-50`, `surface-muted`), not saturated pills.

## Landing page structure

[`frontend/src/pages/LandingPage.tsx`](../frontend/src/pages/LandingPage.tsx)

All four sections are `mx-auto max-w-4xl px-6`; the sections alternate white and
`surface` backgrounds, separated by `border-line`.

1. **Hero** — centred logo, `Osteosarcoma Clinical Trial Explorer`, one paragraph,
   `Browse Trials` primary plus a `How it works` outline button jumping to `#how-it-works`.
2. **Why this exists** — eyebrow, a single bold sentence, then three figures
   (`~1,000` / `Decades` / `300k+`) split by vertical hairlines, each with a
   one-sentence gloss. One colour each: `brand-600`, `accent-700`, `gray-900`.
3. **How it works** — the five pipeline steps as a **static** vertical timeline.
4. **Closing CTA** — `Find a trial that fits` on a `surface` band.

Two details worth knowing before editing:

- The timeline rail is an absolutely positioned `span` per step
  (`top-8 bottom-2 left-[13px]`), drawn behind the numeral circle and omitted on the
  last step.
- `EMPHASISED_STEP` (step 2, AI Classification) is the only step with a filled
  numeral and the only one that renders the three classification chips. It is the
  stage the page exists to explain; the emphasis is deliberate, not state.

The timeline is presentational only — the steps do not expand. An earlier version
made each step a disclosure containing detail prose, three worked classification
examples, and a modal showing the verbatim classification prompt from
[`app/services/ai/prompts.py`](../app/services/ai/prompts.py). That was removed in
favour of the flat five-line summary. If the transparency content is ever wanted
back, it needs the page copy **and** a fresh copy of the backend prompt — nothing
syncs the two automatically.
