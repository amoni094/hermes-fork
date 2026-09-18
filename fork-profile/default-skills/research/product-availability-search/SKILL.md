---
name: product-availability-search
description: Use when hunting a product variant shippable to a country.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Shopping, Availability, Retail, International Shipping]
    related_skills: [product-price-monitor, firecrawl-research, blocked-page-recovery]
triggers:
  - User wants to buy a specific product in a specific colour/size/variant
  - Product is hard to find or user says they've been struggling to locate it
  - Need to verify whether a retailer ships to a specific country (especially AU)
  - One-off "where can I buy X in variant Y that ships to Z"
  - NOT recurring price watching — use product-price-monitor for that
related_skills:
  - product-price-monitor
  - firecrawl-research
  - blocked-page-recovery
---

# Product Availability Search

One-off hunt for a specific product variant (colour, size, model) that is in stock and shippable to the user's country. The task ends when you have confirmed purchasable links — or an honest statement of global scarcity.

For recurring watches, hand off to `product-price-monitor`.

## Search Sequence

### 1. Brand's own regional store first

Always start with the official brand store for the user's country (e.g. `brand.com.au`, `brand.com/en-au`). These are Shopify or similar — `web_extract` the product page directly. The colour/size selector list in the page content tells you what variants are live. If the exact variant is absent, note which colours/sizes are currently listed and move on.

### 2. Parallel web_search for the exact variant

Run two searches in parallel:
- `"[Brand] [product name] [colour] [size] buy online ship [country]"` (no site restriction)
- `"[Brand] [product name] [colour] [size] available stock"` (no site restriction)

Scan results for retailers that explicitly show the variant. Ignore aggregators and SEO listicles — target actual retailer product pages.

### 3. Extract product pages and check variant availability

For each promising retailer, `web_extract` the product URL. Look for:
- Colour/size selector list in page text — confirms the variant exists
- "Add to cart" / "Add to bag" / quantity selectors — confirms it's purchasable
- "Sold out", "Out of stock", "Unavailable" text — eliminates the option
- Pricing in the target-country currency or a recognizable international price

Note: most ecommerce pages render stock status via JavaScript. `web_extract` will capture the static HTML, which may show selectors but not real-time stock state. When in doubt, flag this to the user and give them the link to verify at checkout.

### 4. Check shipping policy for non-regional retailers

For any non-regional retailer that has the variant:
- Check their delivery/shipping page (typically `/pages/delivery`, `/pages/shipping`, or footer link)
- Search: `site:<retailer-domain> international shipping australia`
- If the delivery page 404s or is nav-only, check the retailer homepage description or contact info for geography signals (UK VAT number, US-only ZIP, etc.)
- Look for clear signals: "Free UK delivery" with no international mention = UK only; "worldwide shipping" or no restriction = international likely

When shipping policy is ambiguous and the variant is confirmed, tell the user to add to cart and check checkout — that's the definitive test.

### 5. Report clearly

For each retailer found:
- Name + direct product URL (pinned to the specific colour if the URL supports it)
- Variant confirmed (colour + size visible in page)
- Stock confidence: confirmed in-cart-ready / selector visible but JS-gated / unknown
- Shipping to [country]: confirmed / likely (worldwide claim) / UK-only / unconfirmed (check checkout)
- Price + currency
- Any notable caveats (restock wait, pre-order, etc.)

Always lead with the official brand regional store status even if it doesn't have the variant — it's the cleanest option if stock returns.

## Pitfalls

- **Nav-stuffed pages**: Citrus-Lime (Taunton Leisure, Crib Goch), Magento, and similar platforms embed the entire site nav in the static HTML. `web_extract` will show ~11k chars of nav before any product info. Even with `read_file` pagination, real-time stock is JS-rendered and won't appear.
- **Dynamic stock state**: `web_extract` captures static HTML. A colour/size in the selector list means the variant exists in the catalog, not that it's in stock. For definitive confirmation, the user must try adding to cart.
- **UK-only stores**: Most UK outdoor gear retailers (Taunton Leisure, Crib Goch Outdoor, Cotswold Outdoor) ship UK-only despite appearing prominently in international searches. If the delivery page says "Free UK Delivery" with no international mention, it's UK only.
- **Shopify stores without a public policy page**: If the delivery policy page 404s, check the product page shipping section and the checkout flow. A free-shipping-over-threshold banner without country restriction is a soft signal of international shipping.
- **Don't claim stock is confirmed** when you only verified the variant exists in a selector list. Be explicit about JS-gating.

## Verification

- [ ] Official brand regional store checked first, variant status stated clearly
- [ ] Colour + size confirmed visible in product page content (not just search snippet)
- [ ] Shipping policy verified or explicitly flagged as unconfirmed for each retailer
- [ ] No dead links — all URLs are actual product pages, not search results
- [ ] Stock confidence level is stated for each option

## Reference

See `references/retailer-shipping-notes.md` for known retailer shipping scope facts.
