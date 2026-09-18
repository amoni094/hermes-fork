# Coffee Brewing Recipes — Domain Knowledge Bank

Knowledge base for V60 and general pour-over recipe research.
Load when: researching pour-over recipes, grinder dial-in, brew methods.

## Key Sources (authoritative, in priority order)

1. **James Hoffmann** (YouTube: @jameshoffmann) — evidence-based, well-tested methods;
   video descriptions contain the full written recipe. Best for: general technique baselines.
2. **Lance Hedrick** (YouTube: @LanceHedrick) — competition-adjacent; does blind comparisons;
   good for evaluating rival recipes head-to-head.
3. **Matt Winton** — World Brewers Cup 2021 Champion; 5-pour V60 is competition standard.
4. **Tetsu Kasuya** — 4:6 method inventor; authoritative on the method family.
5. **r/pourover** (Reddit) — active community; ZP6/grinder-specific user reports, dial-in
   threads, and taste comparisons. Real URLs extractable via web_extract after web_search.
6. **Hario Official Channel** — source for champion recipes (Winton 5-pour published there).

## V60 Recipe Landscape (current consensus)

### 4:6 Method (Tetsu Kasuya)
- **Ratio:** 1:15 (e.g. 20g / 300g) standard; devil variant uses ~1:13
- **Temp:** 93°C standard; 88-90°C for medium-light to suppress bitterness
- **Structure:** 40% water in first 2 pours (controls sweetness/acidity), 60% in last 3 pours (controls strength)
- **Grind:** Medium-coarse
- **Total time:** 3:30–4:00
- **Best for:** Medium to medium-dark; highly adjustable
- **Limitation with fast-flow papers:** Longer timing risks under-extraction if drain is too fast

### Hoffmann Better 1-Cup (updated)
- **Ratio:** 1:16.7 (15g / 250g)
- **Temp:** Boiling for light roast; 92-94°C for medium-light
- **Structure:** 50g bloom + swirl → 4 pours of ~50g each, 10s apart, pause between
- **Grind:** Medium-fine
- **Target drawdown:** ~3:00
- **Best for:** Fast-flow papers; forgiving and consistent
- **Pitfall:** 30g method wastes beans during dial-in; 15g version easier to start with

### Matt Winton 5-Pour (World Brewers Cup)
- **Ratio:** ~1:16.9 (16g / 270g)
- **Temp:** 96°C
- **Structure:** Bloom + 4 controlled pulses
- **Best for:** Light/medium-light clarity; avoids channeling; suits conical burrs
- **Source:** Hario Official Channel YouTube

### Osmotic Flow (Scott Rao / Sprometheus)
- Single slow continuous pour after bloom targeting even saturation
- Fast-flow papers help prevent waterlogging
- Praised for clarity and sweetness on light roasts

## Grinder Context

### Timemore ZP6
- Conical burr; mid-tier; decent particle uniformity
- Community-confirmed dial-in for V60 + fast-flow papers: **setting 4** (roughly medium)
- User report (r/pourover): 15g/255g, 17:1 ratio, setting 4, 2:00-2:15 drawdown
- With fast-flow papers: go one click finer than intuition; drain compensates

## Paper Type Impact

**Fast-flow papers** (light tabbed, Hario 02 etc.):
- Shorter contact time = need finer grind to compensate
- Benefits Hoffmann pulsed method over long 4:6 timing
- Osmotic flow works well (no waterlogging risk)
- Target drawdown 2:00-3:00; if over 3:30, grind finer or increase dose

## Temperature for Medium-Light Roast

Consensus from r/pourover and Japanese roaster community:
- **90-92°C** produces sweeter, less bitter cups than boiling for medium-light
- Boiling (100°C) risks bitterness/astringency — Hoffmann recommends it but the community
  widely finds 92°C better for this roast level with a non-competition grinder
- Japanese roasters (Kurasu, Yoshihara) use 90°C even for light roasts

## Research Workflow for Recipe Queries

1. `web_extract` YouTube video description (authoritative channel) — often has full written recipe
2. `web_search site:reddit.com r/pourover [grinder] [recipe]` → get real thread URL → `web_extract`
3. Check for grinder-specific dial-in threads (ZP6, C40, 1Zpresso etc.) — user numbers more
   reliable than generic advice
4. Cross-reference 2-3 sources before recommending; note where community diverges from experts
