---
name: creagen-promo-video
description: "Use when the user wants a vertical 9:16 short-form product ad (Reels, Shorts, TikTok) made from their real product photo: ad goal and audience, a storyboard, a low-cost reference sheet for approval, then one finished clip with on-screen copy and optional audio."
license: MIT
---

# Creagen — short-form product ad

This workflow turns a product photo into a roughly 15-second vertical ad. Creagen's catalog has a guided journey for it (`promo-video`, titled "Short-form Video"); `creagen_journey_start({ ref: "promo-video" })` starts it, and each response carries a `connectorContext` block with the current step's completion criteria and the next journey call. Running the journey is optional; the steps below describe the same flow. The basic generation loop is in the `creagen-generate` skill.

Ask for inputs in plain language, one item at a time, and do not re-ask what the user or an analyzed URL already provided.

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

## 6. Reference sheet (low cost)

- Draw a director reference sheet with a lite image tool (`image2image_nano_banana_2_lite` with the product photo, or `text2image_nano_banana_2_lite` for frames without the product) at 1K. It is a preview for approval, not the deliverable.
- Attach the real product photo on every frame that shows the product.
- Show it with `creagen_show_media` and revise until the user approves.

## 7. The clip

- Quote the cost with `creagen_estimate_credit` (video, the planned duration and audio) and check `creagen_get_credit_balance`. Get the go-ahead.
- Default route: one clip with `reference2video_seedance_2d5`, with the approved sheet frames as `image_urls`, `output_size: "portrait_16_9"` set explicitly (the default is landscape), `duration: "15"` as a quoted string, and `generate_audio: true` when the brief has narration or sound.
- If the user asks for a different model or length, follow that and say in one line what it changes (for example, models capped at 8 seconds need several clips, which costs more).
- On failure, read the error, fix that cause, and retry the same tool. After two failures, tell the user what the error said.
- A response with result URLs is a success even if it also carries an error field.

## 8. Deliver

Show the finished video with `creagen_show_media` once the job is `COMPLETED`, using public URLs only. Offer revisions, noting that a new length, model, or direction means a new generation. If a reusable preference emerged (brand tone, visual style), offer once to save it with `creagen_memory_create`.
