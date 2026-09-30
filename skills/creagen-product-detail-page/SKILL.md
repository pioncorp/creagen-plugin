---
name: creagen-product-detail-page
description: "Use when the user wants a long-form e-commerce product detail page (Korean 상세페이지 style, for Smart Store, Coupang, Cafe24, or a brand store) built from their real product photo: section copy, a color palette taken from the product, and generated section visuals assembled into one vertical page."
license: MIT
---

# Creagen — product detail page

A detail page is a tall, multi-section product page (hero, key claims, benefit sections, gallery, specs, FAQ, call to action). With Creagen, a designer tool drafts the page layout and copy, generation tools make the section images, and you assemble and present the finished page. The basic generation loop (credits, QUEUED → COMPLETED, delivery) is described in the `creagen-generate` skill.

For a single ad banner, `creagen_banner_designer` fits better; for a swipeable card deck, `creagen_carousel_designer`.

## 1. Collect the product facts

Ask one question at a time and skip anything the user already gave:

- At least one real product photo (attach, `creagen_image_uploader`, or a saved product memory via `creagen_memory_list` / `creagen_memory_get`).
- Product name and a short description of what it is.
- Brand name or context.
- Selling points, heritage, or claims the user wants on the page. Use only what the user states; do not invent prices, discounts, certifications, or awards.
- Optional mood: bold commerce style (the default) or refined minimal.

If the user has a product-page URL, `creagen_url_analysis` can pre-fill the facts. Show what it found and let the user correct it.

## 2. Draft the page

Call `creagen_detail_page_designer` with `productImageUrls` (public URLs of the real photo), `product`, `brand`, and optionally `description`, `moodHint`, and `additionalGuidance`. It does not spend generation credits.

It returns:

- `html`: one complete page document, 860px wide, with empty image slots marked by `data-slot="IMG_*"` anchors.
- `imageSlots`: the image plan, one entry per slot, each with `key`, `kind` (`i2i` when the product is visible, `t2i` for scenery or texture without the product), `prompt`, and `aspect`.

The designer's description mentions chat-only render tools; those do not exist in this connector. You render the page yourself in step 5.

## 3. Confirm scope and cost

- Summarize the page plan for the user: the sections and how many images it needs.
- Estimate the image cost with `creagen_estimate_credit` (pass the number of images) and check `creagen_get_credit_balance`.
- Ask for a go-ahead before generating. Offer a cheaper draft pass with `_lite` tools if the user wants to preview first.

## 4. Generate the section images

For each slot in `imageSlots`:

- `kind: "i2i"` → an image-to-image tool (for example `image2image_nano_banana_2`, or `image2image_nano_banana_pro` for final quality) with the real product photo as the input image and the slot `prompt`.
- `kind: "t2i"` → a text-to-image tool (for example `text2image_nano_banana_2`) with the slot `prompt`.
- Match the slot `aspect` where the tool's schema allows it.

Wait until each job is `COMPLETED` before using its `contentUrls`. For product cuts, `creagen_audit_result` can check the result against the product photo; follow its `retryHint` or stop when it reports `terminal: true`.

Keep the product's own label, logo, and packaging text exactly as in the photo. Page headlines and claims belong in the HTML copy, not printed on the product.

## 5. Assemble and present the page

- Insert each generated public URL into the `<img>` inside the anchor whose `data-slot` matches the slot `key`. Leave the rest of the HTML as returned.
- Present the page as an HTML artifact or file the user can open. Show the individual section images with `creagen_show_media` so the user can download them separately.
- Use only public URLs in the page; internal storage URLs do not load outside Creagen.
- Offer targeted revisions: regenerate a single slot, adjust copy, or rerun the designer with `additionalGuidance` from the user's feedback.

## 6. Wrap up

If a reusable preference came up (brand palette, tone, do and don't rules), offer once to save it with `creagen_memory_create`. Skip it if the user declines.
