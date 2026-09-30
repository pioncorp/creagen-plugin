---
name: creagen-generate
description: "Use when the user wants a single marketing or product visual made or edited with Creagen: a product shot, a background swap or removal, a style or brightness edit, a key visual, or a short product clip. Covers choosing a model tool, quoting credits, running the generation, and delivering the finished result. For multi-step deliverables (detail page, short-form ad, UGC review video, lookbook) see the other creagen-* skills."
license: MIT
---

# Creagen — generate and edit product visuals

This skill describes the basic loop for one generation with the Creagen connector: pick the model tool, confirm cost, run it, wait for completion, and deliver. The other `creagen-*` skills build on this loop.

Only use tools that appear in the current session's Creagen tool list, and pass only the fields their input schemas define.

## 1. Understand the brief

- Identify the deliverable: still image or video, the aspect ratio or placement (feed 1:1, story or short-form 9:16, banner 16:9), and whether a real product must appear.
- If the product must appear, get the user's real product photo. It is the only source for what the product looks like and what its label says.
- Read attached images yourself before writing a prompt, so the prompt describes the actual product.
- If the user refers to saved brand or product context ("my brand style", "the jacket I saved"), look it up with `creagen_memory_list` and `creagen_memory_get`. Saved memories are not loaded automatically.
- If the user shares a product-page URL, `creagen_url_analysis` returns structured product data and page images. The call can take up to about 50 seconds; on a timeout, retrying the same URL later usually works.

## 2. Get the input files into Creagen

Generation tools accept an uploaded file's `{ nodeId }` (preferred) or a public URL.

- In clients that render MCP Apps widgets (for example Claude Desktop and claude.ai), `creagen_image_uploader` lets the user drop up to 20 images and returns `nodeId` and `publicUrl` for each.
- In Claude Code or other hosts without widgets, use `request_file_upload` with the local file path, run the returned `curl` command to upload the bytes, then call `finalize_file_upload` to get the `nodeId`.
- A public image URL the user pastes can be passed directly.

## 3. Choose the model tool

Each Creagen generation tool is fixed to one model; the tool name encodes the operation and the model. Read the tool descriptions in the session for current capabilities.

| Task | Tool family (examples) |
|---|---|
| New image from text | `text2image_nano_banana_2`, `text2image_nano_banana_pro`, `text2image_nano_banana_2_lite`, `text2image_gpt_image_2d0`, … |
| Edit or restage a product photo | `image2image_nano_banana_2`, `image2image_nano_banana_pro`, `image2image_nano_banana_2_lite`, `image2image_gpt_image_2d0`, … |
| Remove the background | `background_remove` |
| Video from text | `text2video_seedance_2d5`, `text2video_kling_o3_pro`, `text2video_kling_3d0_standard`, `text2video_gemini_omni_flash_1d1`, … |
| Animate a still | `image2video_seedance_2d5`, `image2video_kling_o3_pro`, `image2video_kling_3d0_pro`, `image2video_gemini_omni_flash_1d1`, … |
| Video that keeps several references (product, person, frames) | `reference2video_seedance_2d5`, `reference2video_seedance_2d0_pro`, `reference2video_seedance_2d0_fast`, `reference2video_gemini_omni_flash_1d1` |
| Video between a first and last frame | `firstlast2video_veo_3d1`, `firstlast2video_veo_3d1_fast`, `firstlast2video_veo_3d1_lite` |
| Edit or extend an existing video | `video2video_*` tools, when they appear in the session's tool list |

Tier guidance:

- `_lite` tools are cheaper and faster; they suit drafts, reference sheets, and picking between options.
- Standard tools (for example `_nano_banana_2`) are a sensible default for finished stills.
- `_pro` and `_4k` tools cost more; offer them for final polish or when the user asks for higher quality.
- Video costs considerably more than images. Seedance reference-to-video reaches 15 seconds in one clip; Veo and Kling clips are shorter, so a longer piece on those models needs several generations.

If the user names a model, use that model's tool when it fits the inputs, and say in one line what changes if it does not.

## 4. Quote credits and confirm before spending

Every generation tool spends the user's Creagen credits.

1. Call `creagen_estimate_credit` with the modality, tier, and provider that correspond to the chosen tool, and the cost-driving inputs you plan to send (duration, output size, audio, number of outputs).
2. For video or batches, also call `creagen_get_credit_balance`; the connector does not inject the balance.
3. Tell the user the estimate (a range is a range; do not quote the maximum as the price) and ask for a go-ahead before any video, batch, or pro-tier run. Warn if the estimate exceeds the balance.

## 5. Run the generation and wait for completion

- A generation tool queues the job and returns a `tixId` with status `QUEUED`. QUEUED means started, not finished.
- In widget-capable clients, a live progress widget is attached to the generation tool's result and shows the media when it finishes. `creagen_show_progress({ tixId, mediaType })` shows the same widget for a job started earlier.
- Without widget support, call `check_generation_status({ tix_id })` about every 10–15 seconds.
- A result is finished only when the status is `COMPLETED` and `contentUrls` is non-empty. Present results only after that.
- If a job fails, read the error, fix that cause (common ones: a duration sent as a number where the schema expects a string, or an unreachable image URL), and retry the same tool. After two failures, stop and tell the user what the error said.

## 6. Check fidelity and deliver

- For edits that must stay faithful to a source (product shots, logos, labels), `creagen_audit_result({ source_image_urls, result_image_urls, edit_prompt })` compares the result to the source. `failed` comes with findings and a `retryHint`; `terminal: true` means stop regenerating and deliver the best version so far; `skipped` means not audited.
- Show results with `creagen_show_media({ urls, mediaType })`. It converts internal storage URLs to public URLs on the server.
- Share only `publicUrl` / `contentUrls` with the user. An `internalUrl` is an internal storage reference that does not open outside Creagen; convert it with `resolve_internal_url` before giving it out.
- Public result URLs expire after a while, so suggest downloading promptly. Everything generated through the connector is also stored in the user's Creagen gallery under the "MCP" filter.

## Product fidelity

Text, logos, and labels on the product come only from the user's product photo and are reproduced exactly. Headlines, prices, offers, and calls to action are on-screen copy (overlays, captions, end cards) and are not printed onto the product or its packaging. Write prompts that keep these two apart.

## Related tools

- `creagen_photographer` suggests shot plans; `creagen_copywriter` writes copy packages; `creagen_banner_designer` and `creagen_carousel_designer` produce banner and card-deck HTML specs. Their outputs are formatted for Creagen's own chat renderer, so use them as source material: turn each `suggestedGenerationPrompt` into a generation call and present HTML specs yourself.
- `creagen_skill_search` / `creagen_skill_get` return saved procedures (built-in and the user's own).
- If a tool returns an authentication error, the user needs to reconnect the Creagen connector.
- `bug_report` files a defect report with Creagen support when something in Creagen is broken.
