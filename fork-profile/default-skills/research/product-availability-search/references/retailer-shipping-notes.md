# Retailer Shipping Notes

Known retailer shipping scope facts from product availability searches. Update as new retailers are confirmed.

## Australia-native / Ships to AU confirmed

- **fjallraven.com.au** — official Fjallraven AU Shopify store. Free shipping on orders over $199 AU. Carries a subset of global colourways — not all colours/sizes available globally appear here. Check product page for current selector list.
- **Falcon Menswear** (falconmenswear.com) — UK Shopify store, banner says "FREE SHIPPING on all orders over £50" without country restriction. No working shipping-policy page (/pages/shipping-policy 404s). Carry checkout to verify AU shipping. Stocked Fjallraven Greenland No.1 Down Jacket in Dark Navy inc. size L (Aug 2026). Notes a 5-7 working day wait on some sizes for restocks from Sweden.

## UK-only confirmed

- **Taunton Leisure** (tauntonleisure.com) — UK outdoor gear retailer. Banner: "Free UK Delivery Over £50". No international delivery offered. Citrus-Lime platform: product pages heavily nav-stuffed.
- **Crib Goch Outdoor** (cribgochoutdoor.com) — UK outdoor gear retailer. Self-describes as "UK delivery, Click & Collect, easy returns". Citrus-Lime platform.
- **Cotswold Outdoor** — UK only (common search result; exclude from AU availability searches).

## US-only / Not reliable for AU

- **Zappos** — US only.
- **Out & Back Outdoor** (outandbackoutdoor.com) — geo-blocks non-US visitors with 403 "You cannot access our site from your current region."
- **Enwild** (enwild.com) — scrape-resistant, stock/shipping unconfirmed.

## Platform notes

- **Citrus-Lime ecommerce**: used by Taunton Leisure, Crib Goch, and others. Product pages dump the entire site nav in static HTML (~11k chars before product content). web_extract truncates mid-nav; read_file pagination gets past nav but stock info is JS-rendered and absent. Delivery policy at /pages/delivery/.
- **Fjallraven official regional stores**: fjallraven.com has region sub-stores (en-us, en-au, en-eu, etc.) but most block automated scraping. Use fjallraven.com.au (Shopify) for AU searches — it responds to web_extract cleanly.
