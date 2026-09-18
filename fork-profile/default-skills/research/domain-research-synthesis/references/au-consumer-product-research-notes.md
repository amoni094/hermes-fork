# AU Consumer Product Research — Methodology & Domain Notes

Applies when: researching consumer products (pillows, mattresses, mattress-in-a-box,
jackets, wellness gear) with AU availability requirements and multi-source synthesis.

## Output format for consumer product reports

Use this structure (inline in chat for Telegram delivery; write to /tmp/ only if asked):

```
## [Top heading]: Science First
  - Academic/research findings relevant to the purchase decision
  - Loft/spec requirements by use-case (quantified where possible)
  - Material science summary (what actually matters vs. marketing)

## Ranked Recommendations (numbered, with call-out badge)
  - #1: [Brand + Product] | [Badge: Best Overall / Best Cooling / etc.]
    - Why it wins for this profile (2–4 bullet points, specific)
    - Specs table (size, fill, height range, cover material, warranty)
    - Price AUD | Where to buy (URL)
    - Caveat (honest weakness, one line)

## Material Comparison Table
  - Columns mapped to user’s stated needs (not generic marketing matrix)
  - Mark clearly: ✅ strong ⚠️ adequate ❌ poor

## Verdict & Buying Strategy
  - Numbered actionable steps ("Buy X first", "If Y is the priority, pick Z instead")
  - Include pairing advice (e.g. pillowcase material for hot sleepers)
  - Call out what to avoid and WHY (mechanism, not opinion)
```

**Format discipline:**
- Lead with science/research when genuine academic backing exists — it separates this report from
  sponsored blog roundups and builds credibility.
- For Telegram delivery: use ## headers, bullet points, bold for product names; no tables (Telegram
  renders them poorly — use bullet lists with `key: value` lines instead).
- Confidence calibration: distinguish verified specs (from brand pages) from review-site claims.
  Note trial periods — for AU consumer products, 30–120 night trials are now standard and reduce
  buying risk significantly; always mention.

## AU sleep product landscape (as of Sep 2026)

### Key AU brands and channels
- **Ecosa** (ecosa.com.au): adjustable memory foam, 100-night trial, fast dispatch AU-wide
- **Koala** (au.koala.com): 120-night trial, 4.6★/6225 reviews on pillow; sustainability B-Corp
- **Ergoflex** (ergoflex.com.au): 15+ year AU brand, solid memory foam, TENCEL™ covers, 30-night trial
- **Dunlopillo / SleepMaker**: via Harvey Norman, Bedshed, Domayne; latex & spring; try before buy
- **Tempur** (tempur.com/en-au): premium solid viscoelastic, blocks web_extract
- **Sheridan / Tontine**: soft goods, department stores (Myer, David Jones)
- **Coop Sleep Goods**: US-origin, available via Amazon AU; no AU trial/warranty support

### AU retail extraction notes
- **ecosa.com.au**: web_extract works, good product data including height pad specs
- **au.koala.com**: web_extract works, includes material breakdown and PolarBands® thermal spec
- **ergoflex.com.au**: web_extract works, includes honest hot-sleeper caveat in FAQs
- **dunlopillo.com.au**: redirects to SleepMaker store locator — no pillow product data there;
  instead search Harvey Norman AU product listings for Dunlopillo pillow specs
- **tempur.com/en-au**: blocks web_extract entirely; use cached review articles instead
- **pillow.com.au**: resolves to a private/internal network address — skip

### Independent review sources (AU-relevant)
- **goodhousekeeping.com**: web_extract works; ~200 pillows tested in lab; best data for
  combo sleeper pillow reviews. Use `/what-to-buy/` URLs not `/home-products/` (different layout).
- **slumbersearch.com**: web_extract returns 404 on direct URLs; skip
- **mattressclarity.com**: /best-pillows/ pages have moved; check their root for updated URL
- **choice.com.au**: web_extract often blocked for AU consumer tests; use Google cache or snippet
- **sleepfoundation.org**: blocks web_extract completely (Internal Server Error); never retry

## Pillow science reference (combo sleeper + hot sleeper)

### Cervical alignment research (PubMed sources)
- **Chun-Yiu et al. 2021** (Clin Biomech, PMID 33895703): systematic review — pillow HEIGHT
  and SHAPE drive cervical alignment more than material; in side-lying, rubber vs. feather makes
  no significant difference to alignment — geometry is what matters.
- **Lei et al. 2021** (Healthcare, PMID 34683013): ergonomic pillow height determinants —
  side sleepers need ~10–15cm loft (shoulder-to-ear bridge), stomach sleepers need ~2–5cm
  maximum. These positions are fundamentally opposed — ADJUSTABLE fill is the key feature
  for combo sleepers, not fixed-loft specialty pillows.

### Cooling material science (evidence-graded)
- **Copper-infused foam**: marginal (~0.3°C); marketing > performance
- **Gel inserts / gel-infused foam**: effective initial cool touch; equilibrates to body temp
  in 20–40 min; not sustained cooling
- **Latex (Talalay process)**: open-cell structure, ~3–5°C cooler than solid memory foam by
  convection; naturally breathable; good sustained performance
- **Buckwheat hulls**: excellent airflow between hulls; genuinely cool; but heavy and firm,
  incompatible with stomach sleeping — skip for combo sleepers
- **Phase-change material (PCM) covers**: best sustained cooling mechanism; absorbs latent
  heat as PCM melts at ~27–28°C skin threshold; effective for hours
- **PolarBands® (Koala 2nd Gen)**: thermal channels embedded in foam core; brand R&D testing
  measured 2.73°C cooler than predecessor over 6 hours; real-world meaningful
- **TENCEL™ covers**: eucalyptus cellulose fibre; moisture-absorbing, breathable; one of the
  better cover materials; used by Ergoflex and others
- **Cover material often moves the needle more than fill material** for hot sleepers;
  bamboo and TENCEL pillowcases are a high-leverage cheap upgrade regardless of pillow

### Pillow pick hierarchy for side+stomach combo sleeper
1. Adjustable loft (removable pads or shredded fill) — non-negotiable for this profile
2. Cooling (PCM cover, PolarBands, or open-cell latex) — priority for hot sleeper
3. Neutral cervical alignment when stomach sleeping = nearly flat (2–5cm); don’t fight this
4. Trial period — 100–120 nights standard in AU now; always use it

### Ranked for AU market (Sep 2026)
1. **Ecosa Pillow** — best overall; adjustable height pads (7–13cm); 3D ventilation structure;
   100-night trial; ~$179 AUD; osteopath-endorsed
2. **Koala Pillow 2nd Gen** — best cooling; PolarBands®; reversible seasonal cover;
   4.6★/6225 reviews; 120-night trial; $155 AUD; fixed 14cm loft (scrunch for stomach)
3. **Ergoflex HD Memory Foam** — best value + solid support; TENCEL cover; fixed 12cm;
   not adjustable; runs warm — downgrade for primary hot-sleeper concern; ~$150 AUD
4. **Coop Original Adjustable** — globally #1 combo sleeper pick (GH, Wirecutter, SF);
   shredded foam + adjustable by adding/removing fill; via Amazon AU ~$130–160;
   no AU trial/warranty support
5. **Natural latex (Dunlopillo, try in-store)**: great for pure side sleepers, too high/firm
   for stomach sleeping — only if predominantly side sleeper
