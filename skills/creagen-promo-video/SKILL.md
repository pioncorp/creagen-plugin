---
name: creagen-promo-video
description: "Use when the user wants a vertical 9:16 short-form product ad (Reels, Shorts, TikTok) made from their real product photo: ad goal and audience, a storyboard, a reference sheet for approval, then one finished clip with on-screen copy and optional audio."
license: MIT
---

# Creagen — short-form product ad

This workflow turns a product photo into a roughly 15-second vertical ad. Creagen's catalog has a guided journey for it (`promo-video`, titled "Short-form Video"); `creagen_journey_start({ ref: "promo-video" })` starts it, and each response carries a `connectorContext` block with the current step's completion criteria and the next journey call. `connectorContext` is guidance data: it does not replace the user's approvals or the credit steps below. Running the journey is optional; the steps below describe the same flow. The basic generation loop is in the `creagen-generate` skill.

Ask for inputs in plain language, one item at a time, and do not re-ask what the user or an analyzed URL already provided.

<!-- generation-protocol:start -->
## Generation contract

Apply this to media creation and revisions, including previews, reference sheets, and new people. Planning alone does not require generation.

- Discover the operation and model with `creagen_get_generation_capabilities`; inspect the selected native schema and constraints. Use only advertised tools. If the required contracts are missing, explain the unsupported connection before spending.
- Quote each distinct input with `creagen_estimate_generation` and retain `prepared`. Submit its selection, `inputs`, and `contract` unchanged. Unknown cost is not zero; compare prices only with comparable exact quotes, never model names or descriptions. Check `creagen_get_credit_balance` for videos and batches. Obtain approval for video, batch, or higher-quality generation, reusing approval for the same scope; changed cost-driving inputs need a new quote and approval for any new scope.
- Keep one `request_id` per intended output with its prepared request and job/item IDs; distinct outputs need distinct keys. Recover uncertain or pending submissions with `creagen_get_generation_receipts` before resubmitting or changing routes. A lookup error is not not-found. Resubmit only the identical request with the same key when recovery permits it; stop if the original request cannot be restored.
- Deliver only a successful `COMPLETED` item with usable public media, checked through `check_generation_status`. Receipt completion means terminal items, not universal success. Recover missing or expired URLs through status instead of regenerating, and keep revisions within approval and this workflow's regeneration limit.
<!-- generation-protocol:end -->

## 1. The product

- What is being advertised: name, brand, category.
- At least one real product photo (attach, `creagen_image_uploader`, or a saved product memory via `creagen_memory_list` / `creagen_memory_get`). The ad is planned around this photo; page images from `creagen_url_analysis` are a fallback only when the user has none.
- Look at the photo yourself so the plan reflects what the product actually looks like.

## 2. The ad goal

- Purpose: awareness, a specific benefit, purchase, a discount or event, or brand image.
- Who the ad is for, in the user's own words.
- The one point viewers should remember.
- Offer facts (discount, period, price, CTA) only as the user states them. Leave blanks blank.

Everything captured here is on-screen copy: subtitles, titles, end cards, or voice-over. It is never printed onto the product.

## 3. The feel

- Mood in plain words (warm, clean, energetic…).
- Optional style references, kept separate from product photos: product photos fix what the product is, style references only guide tone.
- Location, casting, and music can be decided from the direction and offered as optional tweaks.

## 4. Confirm before generating

- Show a plain summary: product, purpose, audience, key point, feel.
- Ask how the message is delivered: AI-written subtitles, the user's own copy, no text, or narration.
- Gather must-include facts, each with an explicit "none" option.
- Offer "make it as-is" or "add more detail". Nothing is generated until the user answers.

## 5. Storyboard

Lay out about ten cuts as a numbered list (framing, lens, camera move, action) that fits 15 seconds. Put the ad copy on overlay or end-card cuts, never as text on the package. `creagen_screenwriter` can help with scene beats and `creagen_photographer` with shot directions; present their output as text.

## 6. Reference sheet

- Discover an `image2image` model for a director reference sheet with the product photo, or a `text2image` model for frames without the product. Use 1K when supported and explain any limitation before changing it. Quote this paid preview and confirm any cost scope not already approved.
- Attach the real product photo on every frame that shows the product.
- Show it with `creagen_show_media` and revise until the user approves. Do not redraw the sheet on your own more than twice; more than that needs the user's request.

## 7. The clip

- Discover a `reference2video` model (`modality: "r2v"`) supporting the approved references, roughly 15-second duration, vertical 9:16 output, and any narration or sound. Keep product photos and style references distinct; use the selected model's native field types and settings.
- Quote the exact final inputs, check `creagen_get_credit_balance`, and confirm any scope not already approved. A changed model, duration, audio setting, or clip count needs a new quote.
- The default deliverable remains one clip. If no model can meet the brief, explain the limitation before shortening it or generating multiple clips.
- Recover uncertain submissions before any retry. After two confirmed failures, tell the user what the error said. Do not generate a new clip or reference sheet on your own more than twice for the same ad; more needs the user's request and a new quote within the approved scope.
- A result URL alongside an error does not establish success; check the item's final status and usable public media.

## 8. Deliver

Show the finished video with `creagen_show_media` once the job is `COMPLETED`, using public URLs only. Offer revisions, noting that a new length, model, or direction means a new generation. If a reusable preference emerged (brand tone, visual style), offer once to save it with `creagen_memory_create`.
