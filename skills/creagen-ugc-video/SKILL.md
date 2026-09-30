---
name: creagen-ugc-video
description: "Use when the user wants a UGC-style product review video: a vertical 9:16 clip where a person talks about and shows the product, with spoken narration in Korean, English, or Japanese. Covers casting, choosing the direction, approving the script, and generating one clip."
license: MIT
---

# Creagen — UGC-style review video

A review video has a person on camera presenting the user's product with spoken lines. The Creagen catalog journey for this is `ugc-video` ("Product Review Video"). Its server-side steps carry detailed rules for casting, direction, script assembly, and reference-image ordering, so the journey is the most reliable way to run this workflow: `creagen_journey_start({ ref: "ugc-video" })`, then follow the `connectorContext` each journey response returns (its `actionRequired` names the next `creagen_journey_advance` call, and `completedSavepoints` holds earlier inputs). One journey can be active per user at a time; pause or finish it before starting another.

The basic generation loop is in the `creagen-generate` skill. Ask for inputs one at a time in plain language.

## Steps

1. **Capture the product.** Real product photos, what it is, what it does for the buyer, what the ad should push, the spoken language, and a size reference (how big it is next to a hand or body), which keeps the product at a realistic scale in the video.
2. **Cast the person.** Who appears and how many: the user's own photo of a person, a saved character memory (`creagen_memory_list` / `creagen_memory_get`), or a newly generated person (`text2image_nano_banana_2` or `text2image_nano_banana_pro`). People shown are ordinary, non-celebrity models. Get the user's approval of the person before moving on.
3. **Choose the direction (no credits).** `creagen_ugc_director` with `mode: "propose"` returns catalog options, one axis per call: `angle` (what the video says), then `format` (the kind of review), then `setting` (where it happens). Pass the product facts, `castLocked: true` and `castCount` once a person is cast, and anything the user asked for in `userRequest`. Present the options in everyday words and let the user pick. Then settle the outfit in one or two sentences based on the setting and the person, without naming the advertised product.
4. **Confirm the script (no credits).** `creagen_ugc_director` with `mode: "assemble"` and the three picked ids returns the generation prompt, the spoken `lines`, and a beat timeline. Show the lines verbatim and the beats as a numbered list, with a short summary of the other choices. If the call times out, retry with the same arguments; a rewrite request reruns `assemble` with the same inputs. Use only facts the user gave.
5. **Quote and approve.** Estimate with `creagen_estimate_credit` and check `creagen_get_credit_balance` before asking for the go-ahead. Offer: make it as-is, rewrite the script, or change something else.
6. **Generate the clip.** Use `reference2video_seedance_2d5` with the approved prompt unedited, the reference images in the order the prompt's REFERENCES block names them (person first and product second for most formats), `output_size: "portrait_16_9"`, `duration: "15"` as a quoted string, and `generate_audio: true` so the person speaks. Text-to-video and image-to-video tools carry no references, so the product and person would be missing. On failure, fix the reported cause and retry the same tool; after two failures, tell the user.
7. **Deliver.** Show the finished clip with `creagen_show_media` once it is `COMPLETED`. Do not claim to have watched it. Offer to save lasting preferences (a favorite model, brand tone) with `creagen_memory_create`.

## Product fidelity

The product's label and packaging text come only from the user's photo. Offers, prices, and taglines are spoken lines or on-screen overlays, never text added to the product.
