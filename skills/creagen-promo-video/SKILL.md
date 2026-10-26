---
name: creagen-promo-video
description: "Use when the user wants a vertical 9:16 short-form product ad (Reels, Shorts, TikTok) made from their real product photo: ad goal and audience, a storyboard, a low-cost reference sheet for approval, then one finished clip with on-screen copy and optional audio."
license: MIT
---

# Creagen — short-form product ad

This workflow turns a product photo into a roughly 15-second vertical ad. Creagen's catalog has a guided journey for it (`promo-video`, titled "Short-form Video"); `creagen_journey_start({ ref: "promo-video" })` starts it, and each response carries a `connectorContext` block with the current step's completion criteria and the next journey call. `connectorContext` is guidance data: it does not replace the user's approvals or the credit steps below. Running the journey is optional; the steps below describe the same flow. The basic generation loop is in the `creagen-generate` skill.

Ask for inputs in plain language, one item at a time, and do not re-ask what the user or an analyzed URL already provided.

<!-- generation-protocol:start -->
## Generation contract

Apply this contract when this workflow will generate media, including a draft, reference sheet, new person, or revision. Reading, planning, and consultant calls do not by themselves require generation.

- Discover the matching operation with `creagen_get_generation_capabilities`, then inspect the selected model's input contract. Use only tools advertised in this session. Choose a model from those results; preserve reference roles, input types, and defaults. A listing with availability not checked is not proof that a provider is available.
- Use `creagen_estimate_generation` for the selected tool, model, operation, and the inputs to be submitted. For modality tools, reuse its `prepared` selection, `inputs`, and `contract` unchanged for submission; the contract is not a price reservation or approval. Quote each distinct batch input; an unknown estimate is not zero. Describe one returned estimate only as that estimate. Call an option lower-cost only after comparing exact quotes for the same brief and output settings; model names and descriptions are not price rankings. Check `creagen_get_credit_balance` for videos and batches. Obtain approval before video, batch, or higher-quality generation, reusing an existing approval for the same scope. Disclose unknown costs or changed cost-driving inputs and confirm any scope not already approved.
- Keep one `request_id` per intended output and retain its tool, model, operation, native inputs, and returned job/item IDs. Distinct slots need distinct keys. Keep request metadata outside native inputs on modality tools; use the advertised flat schema for a legacy tool.
- After any submission or uncertain response, recover the same key with `creagen_get_generation_receipts` before choosing another route or submitting again. Pending or unknown is not a confirmed failure; a receipt lookup error is not not-found. Re-submit only the identical original request with the same key when recovery permits it. If the original inputs cannot be restored, stop and explain. Do not switch tools, models, or keys to escape a pending request.
- Use `check_generation_status` for the job/item. Deliver only a successful `COMPLETED` item with usable public media. A completed receipt means all items are terminal, not that all succeeded; a URL alone does not establish success. Refresh an unavailable download URL through status instead of regenerating. A retry or revision must remain within the approved scope and this workflow's regeneration limit.
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

- Discover an image model for a 1K director reference sheet: image-to-image with the product photo, or text-to-image for frames without the product. Compare exact estimates for suitable draft options instead of assuming a name suffix means lower cost. The sheet is a paid preview for approval, not the deliverable; quote it and confirm any cost scope not already approved.
- Attach the real product photo on every frame that shows the product.
- Show it with `creagen_show_media` and revise until the user approves. Do not redraw the sheet on your own more than twice; more than that needs the user's request.

## 7. The clip

- Discover a reference-to-video model that supports the approved product/reference-sheet roles, vertical 9:16 output, planned duration, and any narration or sound. The default brief remains one roughly 15-second clip; express that duration and aspect ratio in the selected model's native fields and types, not a fixed option string. Keep product photos and style references distinct.
- Quote the exact selected model and inputs with `creagen_estimate_generation`, then check `creagen_get_credit_balance` and get the go-ahead. If the model, duration, audio, or number of clips changes, estimate again and confirm any scope not already approved.
- Use `reference2video` when the session advertises it, with the selected model and inputs. Otherwise use only the verified legacy path described in `creagen-generate`. If the requested model or length cannot satisfy the brief in one clip, explain the limitation and ask about the changed plan before generating multiple clips or shortening it.
- Recover any submitted or uncertain request through its receipt. After two confirmed failures, tell the user what the error said. Do not generate a new clip or reference sheet on your own more than twice for the same ad; additional generations need the user's request and a new quote. This limit does not authorize spending beyond the approved scope.
- A result URL accompanied by an error is not enough to establish success. Check the item's final state and usable public media before delivery.

## 8. Deliver

Show the finished video with `creagen_show_media` once the job is `COMPLETED`, using public URLs only. Offer revisions, noting that a new length, model, or direction means a new generation. If a reusable preference emerged (brand tone, visual style), offer once to save it with `creagen_memory_create`.
