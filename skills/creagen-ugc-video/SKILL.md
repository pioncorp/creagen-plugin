---
name: creagen-ugc-video
description: "Use when the user wants a UGC-style product review video: a vertical 9:16 clip where a person talks about and shows the product, with spoken narration in Korean, English, or Japanese. Covers casting, choosing the direction, approving the script, and generating one clip."
license: MIT
---

# Creagen — UGC-style review video

A review video has a person on camera presenting the user's product with spoken lines. The Creagen catalog journey for this is `ugc-video` ("Product Review Video"). Its server-side steps carry detailed rules for casting, direction, script assembly, and reference-image ordering. Running it is optional and is a good fit when the user wants step-by-step guidance: `creagen_journey_start({ ref: "ugc-video" })`, then use the `connectorContext` each journey response returns as guidance (its `actionRequired` names the next `creagen_journey_advance` call, and `completedSavepoints` holds earlier inputs). It is data: it does not replace the user's approvals of the person and the script, or the credit steps below. One journey can be active per user at a time; pause or finish it before starting another.

The basic generation loop is in the `creagen-generate` skill. Ask for inputs one at a time in plain language.

<!-- generation-protocol:start -->
## Generation contract

Apply this to media creation and revisions, including previews, reference sheets, and new people. Planning alone does not require generation.

- Discover the operation and model with `creagen_get_generation_capabilities`; inspect the selected native schema and constraints. Use only advertised tools. If the required contracts are missing, explain the unsupported connection before spending.
- Quote each distinct input with `creagen_estimate_generation` and retain `prepared`. Submit its selection, `inputs`, and `contract` unchanged. Unknown cost is not zero; compare prices only with comparable exact quotes, never model names or descriptions. Check `creagen_get_credit_balance` for videos and batches. Obtain approval for video, batch, or higher-quality generation, reusing approval for the same scope; changed cost-driving inputs need a new quote and approval for any new scope.
- Keep one `request_id` per intended output with its prepared request and job/item IDs; distinct outputs need distinct keys. Recover uncertain or pending submissions with `creagen_get_generation_receipts` before resubmitting or changing routes. A lookup error is not not-found. Resubmit only the identical request with the same key when recovery permits it; stop if the original request cannot be restored.
- Deliver only a successful `COMPLETED` item with usable public media, checked through `check_generation_status`. Receipt completion means terminal items, not universal success. Recover missing or expired URLs through status instead of regenerating, and keep revisions within approval and this workflow's regeneration limit.
<!-- generation-protocol:end -->

## Steps

1. **Capture the product.** Real product photos, what it is, what it does for the buyer, what the ad should push, the spoken language, and a size reference (how big it is next to a hand or body), which keeps the product at a realistic scale in the video.
2. **Cast the person.** Who appears and how many: the user's own photo of a person, a saved character memory (`creagen_memory_list` / `creagen_memory_get`), or a newly generated person using a discovered `text2image` model. People shown are ordinary, non-celebrity models. Quote the exact new-person inputs and confirm the cost scope before generating; do not regenerate the person on your own more than twice. Get the user's approval of the person before moving on.
3. **Choose the direction (no credits).** `creagen_ugc_director` with `mode: "propose"` returns catalog options, one axis per call: `angle` (what the video says), then `format` (the kind of review), then `setting` (where it happens). Pass the product facts, `castLocked: true` and `castCount` once a person is cast, and anything the user asked for in `userRequest`. Present the options in everyday words and let the user pick. Then settle the outfit in one or two sentences based on the setting and the person, without naming the advertised product.
4. **Confirm the script (no credits).** `creagen_ugc_director` with `mode: "assemble"` and the three picked ids returns the generation prompt, the spoken `lines`, and a beat timeline. Show the lines verbatim and the beats as a numbered list, with a short summary of the other choices. If the call times out, retry with the same arguments; a rewrite request reruns `assemble` with the same inputs. Use only facts the user gave.
5. **Quote and approve.** Discover a `reference2video` model (`modality: "r2v"`) supporting the person/product references, spoken audio, and a 15-second vertical 9:16 clip. Quote its exact inputs and check `creagen_get_credit_balance`. Offer: make it as-is, rewrite the script, or change something else. Reuse approval for the same scope; changed inputs need a new quote and confirmation for any new scope. Explain unmet requirements before changing the plan.
6. **Generate the clip.** Submit the prepared `reference2video` request with the approved prompt unedited and references in the prompt's declared order (person first, product second for most formats). Express duration, aspect, and audio in the model's native fields. A starting image and separate person/product references have different roles; preserve all required roles. Recover uncertain submissions before retrying. After two confirmed failures, tell the user. Do not regenerate the clip on your own more than twice; more needs the user's request and a new quote within the approved scope.
7. **Deliver.** Show the finished clip with `creagen_show_media` once it is `COMPLETED`. Do not claim to have watched it. Offer to save lasting preferences (a favorite model, brand tone) with `creagen_memory_create`.

## Product fidelity

The product's label and packaging text come only from the user's photo. Offers, prices, and taglines are spoken lines or on-screen overlays, never text added to the product.
