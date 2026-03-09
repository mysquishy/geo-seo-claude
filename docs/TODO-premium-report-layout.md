# Premium Report Layout Improvements

## Problems

1. **Cover page whitespace** — Spacer(60) + 200x200 gauge = half page empty. Fix: shrink gauge to 140, add key highlights beside it in 2-column layout.

2. **Aggressive page breaks** — Every section forces new page even at 30% fill. Fix: remove most PageBreak(), use KeepTogether, let content flow.

3. **Duplicate platform data** — Chart and table show identical info stacked. Fix: keep chart only, add one-line insights per platform.

4. **Thin executive summary** — One sentence when auto-generated. Fix: 3-4 paragraphs (score context, strongest/weakest, opportunity, improvement estimate).

5. **Findings lack business impact** — Just technical descriptions. Fix: add "Why This Matters" with revenue/visibility impact per finding.

6. **Action plan no effort estimates** — Just action items. Fix: add time, difficulty, score impact (e.g., "10 min, +8 to GEO score").

7. **Missing sections** — Need: Score Improvement Forecast (current vs projected), competitor comparison placeholder, Next Steps CTA.

8. **Loose spacing** — spaceAfter=12 throughout should be 4-6 for tighter professional feel.

## Target

6-8 dense pages, every page >80% utilized, every finding has a "so what", every action has effort + impact.

## Files

- scripts/generate_premium_report.py
- skills/geo-report-premium/SKILL.md (if new input data needed)
