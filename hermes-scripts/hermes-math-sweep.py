#!/usr/bin/env python3
"""
hermes-math-sweep.py

Runs the hermes-research-sweep pipeline for math-only categories,
then immediately passes results through math-paper-interpreter.py
with primer context loaded.

Usage:
  python3 hermes-math-sweep.py [--dry-run] [--limit N]
"""

import sys, json, time, importlib.util, argparse
from pathlib import Path
from datetime import datetime, timezone

# ── Load sweep and interpreter modules ────────────────────────────────────────

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

SCRIPTS = Path("~/.hermes/scripts").expanduser()
CACHE   = Path("~/.hermes/cache/research").expanduser()

sweep = load_module("sweep",       SCRIPTS / "hermes-research-sweep.py")
interp = load_module("interpreter", SCRIPTS / "math-paper-interpreter.py")

# ── Math category keys ────────────────────────────────────────────────────────

CORE_AGENT = {
    'reasoning_planning','tool_use','memory','multi_agent','evaluation',
    'self_improvement','agentic_rag','rl_theory_comprehensive',
    'llm_emergence_theory','agent_adaptation_theory','rlhf_theory',
    'representation_interp','eval_uncertainty_fairness','moe_theory',
    'federated_learning_theory','diffusion_processes','monte_carlo_methods',
    'formal_verification_agent','logic_semantics_agent','verifiability',
    'formal_language_automata','multiagent_systems_theory',
}

MATH_CATS = {k: v for k, v in sweep.CATEGORIES.items() if k not in CORE_AGENT}

# ── Argument parsing ──────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Skip API calls, show what would run')
parser.add_argument('--limit', type=int, default=60,
                    help='Max papers to interpret per run (default: 60 to avoid cron timeout; 0=all)')
args = parser.parse_args()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[hermes-math-sweep] Math-only sweep: {len(MATH_CATS)} categories")
    print(f"[hermes-math-sweep] Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would sweep categories:")
        for k in sorted(MATH_CATS):
            print(f"  {k}: {MATH_CATS[k]['arxiv_cats']}")
        print(f"\nPrimers available:")
        for k in sorted(MATH_CATS):
            p = interp.load_primer(k)
            print(f"  {k}: {'OK ' + str(len(p)) + ' chars' if p else 'MISSING'}")
        return

    # ── Step 1: Run sweep for math cats only ──────────────────────────────────
    print("[hermes-math-sweep] Step 1: Running sweep for math categories...")

    # Temporarily patch CATEGORIES in the sweep module to math-only
    original_cats = sweep.CATEGORIES
    sweep.CATEGORIES = MATH_CATS

    # Use a separate seen cache for math sweeps so math-specific dedup is
    # independent from the full weekly sweep's seen state.
    original_seen_file = sweep.SEEN_FILE
    sweep.SEEN_FILE = sweep.CACHE_DIR / "seen_papers_math.json"

    # Also suppress arXiv listing harvest for math categories.
    # Listing pages for math.AT/cs.IT/math.CO etc. return all recent papers in that
    # field regardless of AI relevance — thousands of pure-math papers with no
    # connection to agent systems. Only the targeted keyword searches are useful here.
    original_listings = sweep.sweep_arxiv_listings

    def math_listings_suppressed(arxiv_cats):
        # Allow only core CS/AI cats (already harvested by the pre-loop block)
        allowed = {'cs.AI', 'cs.CL', 'cs.MA', 'cs.LG', 'cs.SE'}
        if any(c in allowed for c in arxiv_cats):
            return original_listings(arxiv_cats)
        return []  # suppress math.*/stat.*/quant-ph listing pages

    sweep.sweep_arxiv_listings = math_listings_suppressed

    try:
        all_papers, new_papers = sweep.run_sweep()
    finally:
        sweep.CATEGORIES = original_cats
        sweep.sweep_arxiv_listings = original_listings
        sweep.SEEN_FILE = original_seen_file

    print(f"[hermes-math-sweep] Sweep complete: {len(new_papers)} new math papers ({len(all_papers)} total found)")
    print()

    # Save a math-specific sweep output
    math_sweep_out = CACHE / 'hermes-math-sweep-latest.json'
    _tmp_math_sweep_out = math_sweep_out.with_suffix('.tmp')
    _tmp_math_sweep_out.write_text(json.dumps({
        'sweep_date': datetime.now(timezone.utc).isoformat(),
        'new_paper_count': len(new_papers),
        'new_papers_flat': new_papers,
        'all_papers': all_papers,
    }, indent=2, default=str))
    _tmp_math_sweep_out.replace(math_sweep_out)
    print(f"[hermes-math-sweep] Math sweep saved: {math_sweep_out}")

    # ── Step 2: Fetch abstracts + interpret with primers ──────────────────────
    print()
    print("[hermes-math-sweep] Step 2: Interpreting papers with primer context...")

    if args.limit:
        new_papers = new_papers[:args.limit]
        print(f"[hermes-math-sweep] Limited to {args.limit} papers")

    spikes = []
    optimizations = []
    skipped = 0
    errors = 0

    for i, paper in enumerate(new_papers, 1):
        cat = paper.get('category', '')
        pid = paper.get('id', '')
        title = paper.get('title', '') or pid
        arxiv_id = paper.get('arxiv_id', '')

        # Load primer for this category
        primer = interp.load_primer(cat)

        # Fetch abstract if we have an arXiv ID
        abstract = paper.get('abstract', '')
        if not abstract and arxiv_id:
            try:
                fetched = interp.fetch_abstract(arxiv_id)
                abstract = fetched.get('abstract', '')
                if fetched.get('title'):
                    title = title or fetched['title']
                time.sleep(0.5)
            except Exception as e:
                pass

        paper_full = {**paper, 'title': title, 'abstract': abstract}
        if primer:
            paper_full['primer'] = primer[:2000]

        try:
            r = interp.interpret_paper(paper_full, cat)
        except Exception as e:
            errors += 1
            continue

        if r['result'] == 'SPIKE':
            spikes.append({**r, 'id': pid, 'title': title, 'category': cat,
                          'arxiv_id': arxiv_id, 'url': paper.get('url',''),
                          'primer_loaded': bool(primer)})
            flag = 'SPIKE'
        elif r['result'] == 'OPTIMIZATION':
            optimizations.append({**r, 'id': pid, 'title': title, 'category': cat,
                                  'arxiv_id': arxiv_id, 'url': paper.get('url',''),
                                  'primer_loaded': bool(primer)})
            flag = 'OPT'
        else:
            skipped += 1
            flag = 'skip'

        conf = r.get('confidence','?')
        if flag != 'skip':
            print(f"  [{i:3d}/{len(new_papers)}] {flag} [{conf}] [{cat}] {title[:70]}")

    # ── Step 3: Save interpretation results ───────────────────────────────────
    print()
    output = {
        'sweep_date': datetime.now(timezone.utc).isoformat(),
        'math_categories': len(MATH_CATS),
        'papers_found': len(new_papers),
        'spikes': spikes,
        'optimizations': optimizations,
        'skipped': skipped,
        'errors': errors,
    }

    out_path = CACHE / 'math-interpretation-latest.json'
    out_path.write_text(json.dumps(output, indent=2, default=str))

    # ── Step 4: Summary ───────────────────────────────────────────────────────
    print(f"[hermes-math-sweep] Done.")
    print(f"  Papers found:    {len(new_papers)}")
    print(f"  Spikes:          {len(spikes)}")
    print(f"  Optimizations:   {len(optimizations)}")
    print(f"  Skipped:         {skipped}")
    print(f"  Errors:          {errors}")
    print()

    if spikes:
        print("SPIKE candidates:")
        for s in sorted(spikes, key=lambda x: {'high':0,'medium':1,'low':2}.get(x.get('confidence','low'),2)):
            primer_tag = ' [primer]' if s.get('primer_loaded') else ''
            print(f"  [{s['confidence'].upper()}]{primer_tag} [{s['category']}]")
            print(f"    {s['title'][:80]}")
            print(f"    {s.get('url','')}")
            print(f"    Hypothesis: {s.get('hypothesis','')[:120]}")
            print()

    if optimizations:
        print("OPTIMIZATION candidates:")
        for o in sorted(optimizations, key=lambda x: {'high':0,'medium':1,'low':2}.get(x.get('confidence','low'),2)):
            primer_tag = ' [primer]' if o.get('primer_loaded') else ''
            print(f"  [{o['confidence'].upper()}]{primer_tag} [{o['category']}]")
            print(f"    {o['title'][:80]}")
            print(f"    {o.get('url','')}")
            print(f"    Hypothesis: {o.get('hypothesis','')[:120]}")
            print()

    print(f"Full output: {out_path}")


if __name__ == '__main__':
    main()
