# Creagen for Claude

Creagen is a marketing creative tool for product sellers and brand teams, made by PION Corporation. This plugin connects Claude to your Creagen account and adds workflow skills for producing marketing and product design assets: product photos and edits, e-commerce detail pages, short-form product ads, UGC-style review videos, and fashion lookbooks.

The plugin uses AI image and video generation models (for example Google Nano Banana and Veo, OpenAI GPT Image, Kling, Seedance, and Runway) through Creagen's hosted connector. Generations run on Creagen's servers and are billed in Creagen credits on your account.

## What's included

- **Creagen connector** (`.mcp.json`): a remote MCP server at `https://agent.vcat.ai/api/mcp/creagenOfficialMCPServer/mcp`. It provides the generation tools (one tool per model), credit estimates and balance, file upload, progress and media widgets, your saved Creagen memories and chat rooms, expert consultant tools (photographer, copywriter, screenwriter, banner, carousel, detail-page, and UGC designers), result audit, and guided journeys.
- **Skills**: Markdown instructions that describe how to combine those tools for common marketing deliverables.

| Skill | Use it for |
|---|---|
| `creagen-generate` | One image or video: pick a model tool, quote credits, generate, wait for completion, check fidelity, and deliver. |
| `creagen-product-detail-page` | A long-form e-commerce detail page built from a real product photo, with generated section visuals. |
| `creagen-promo-video` | A 9:16 short-form product ad: goal, storyboard, low-cost reference sheet, then one finished clip. |
| `creagen-ugc-video` | A UGC-style review video with a person presenting the product and spoken narration. |
| `creagen-lookbook` | Virtual try-on, multi-angle studio shots, and a retouched fashion lookbook set. |

The skills are instructions only. The plugin contains no scripts, hooks, or executables.

## Requirements

- A Creagen account. Sign up at [creagen.vcat.ai](https://creagen.vcat.ai).
- Creagen credits. Image and video generation spend credits on your account; the skills ask Claude to show a credit estimate and get your go-ahead before videos, batches, and higher-quality tiers. Estimates, balance checks, consultant tools, and journeys do not spend generation credits.
- On first use, sign in to Creagen through the connector's OAuth flow.

## Install

**From the Claude directory**: find Creagen in the plugin directory on claude.ai, add it, then connect the Creagen connector from the plugin's Connectors tab and sign in.

**In Claude Code, from this repository as a marketplace**:

```bash
/plugin marketplace add pioncorp/creagen-plugin
/plugin install creagen@creagen
```

Then run `/mcp` to authenticate the `creagen` server.

**Connector only (no skills)**: in claude.ai, go to Settings → Connectors → Add custom connector and enter:

```
https://agent.vcat.ai/api/mcp/creagenOfficialMCPServer/mcp
```

## Examples

- "Turn this product photo into a clean white-background shot and a lifestyle shot on a marble counter."
- "Make a detail page for this cream from the photo and these selling points."
- "Create a 15-second vertical ad for my sneakers aimed at runners."
- "Make a review video where a woman in her twenties talks about this cold brew."
- "Put these two jackets on a model and give me front, side, and walking shots."

## Data and privacy

When you use the connector, Claude sends Creagen the information needed to run each tool: your prompts, the images or videos you upload or link, URLs you ask it to analyze, and the tool inputs. Creagen processes these on its servers and passes generation requests to the AI model providers listed above. Generated media, uploads, memories, skills, plans, and journey progress are stored in your Creagen account; results made through the connector appear in your Creagen gallery under the "MCP" filter. The plugin itself stores nothing and sends data nowhere other than the Creagen connector.

- Privacy policy: https://vcat.ai/policy/privacy-policy
- Terms of service: https://vcat.ai/policy/terms-of-service

## Support

- Help center: https://creagen.vcat.ai/help
- Email: help@vcat.ai

## License

The skill text and manifests in this repository are released under the MIT License (see `LICENSE`). Use of the Creagen service is governed by the Creagen terms of service.
