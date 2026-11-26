# Design notes

## References looked at (26 Nov 2026, Playwright screenshots in refs/, not committed)
1. Our World in Data, Life Expectancy: chart first, plain prose, a source line under every chart.
2. Rest of World, AI Elections Tracker: one strong colour idea carried through the whole page.
3. The Hindu, Data Journalism: Indian newsroom tone, serif headlines, red as the only accent.
4. The Pudding (home + a story): one big interactive moment, prose wraps around it.
5. Reuters Graphics: restrained axes, direct labels, no legend boxes when labels fit.
6. FT Visual and Data (ig.ft.com): annotation sits on the chart, not in a caption.
7. Bloomberg Graphics: big type over a full-width chart in the hero.
8. Indian Express Explained: explainer structure, short sections, one point each.
9. Datawrapper's style: thin lines, recessive gridlines, units in the axis title.
10. NJDG itself: the source; what not to do (tile wall, counters, 3D pies).

## North star: Our World in Data
Chart is the story. Every chart carries its own title, unit, source line and a one line "what this means".
I take OWID's rigour, not its look (no navy, no Lato).

## Identity: the court file
Indian court records travel in pale green government file covers, tied with red tape (lal feeta).
- Paper `#E4EBE6` (file-cover green, cool, not cream)
- Ink `#15261F` (bottle green black, body text and the "cases filed" series)
- Muted `#5E7A70` (secondary text, the "cases closed" series)
- Rule `#B9C8C0` (gridlines, hairlines)
- Red tape `#B4232A` (the only accent: the backlog gap and the witness stage)
- Card surface for the model `#F3F6F4`

## Type (3 faces, each with one job)
- Bricolage Grotesque (opsz), headlines: tight, a bit civic-poster.
- Source Serif 4, body prose: reads like a report.
- IBM Plex Sans Condensed, numbers and chart labels, tabular figures.

## Layout
Single reading column (about 68ch) with charts breaking out to a wider measure (1120px).
Left aligned everywhere. No cards except the what-if model (it is a tool, so it gets a surface).
No stat tiles in the hero: the hero is the backlog curve itself, full width, with two annotations.

## Motion
One moment: the hero curve draws in once on load. Everything else is still. Reduced motion: no draw.

## Rules kept
No all-caps labels, no eyebrows, no numbered markers, no purple, no Inter/Roboto/system fonts.
