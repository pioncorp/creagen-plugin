[English](README.md) · [한국어](README.ko.md) · **日本語**

# Creagen for Claude

Creagen は、PION Corporation が提供する、商品販売者やブランドチーム向けのマーケティングクリエイティブツールです。このプラグインは Claude をお使いの Creagen アカウントに接続し、マーケティング・商品デザイン素材を制作するためのワークフロースキルを追加します。対象は、商品写真の生成・編集、EC 商品詳細ページ、ショート動画広告、UGC スタイルのレビュー動画、ファッションルックブックです。

本プラグインは、Creagen がホストするコネクタを通じて AI 画像・動画生成モデル(例: Google Nano Banana・Veo、OpenAI GPT Image、Kling、Seedance)を利用します。生成は Creagen のサーバー上で実行され、お客様のアカウントの Creagen クレジットが消費されます。

## 含まれるもの

- **Creagen コネクタ** (`.mcp.json`): リモート MCP サーバー `https://agent.vcat.ai/api/mcp/creagenOfficialMCPServer/mcp` です。生成ツール(モデルごとに 1 ツール)、クレジット見積もりと残高、ファイルアップロード、進行状況・メディアウィジェット、保存済みの Creagen メモリーとチャットルーム、専門コンサルタントツール(フォトグラファー、コピーライター、脚本家、バナー・カルーセル・詳細ページ・UGC デザイナー)、結果の検証、ガイド付きジャーニーを提供します。
- **スキル**: よく使われるマーケティング成果物を作る際に、これらのツールをどう組み合わせるかを記述した Markdown の指示文です。

| スキル | 用途 |
|---|---|
| `creagen-generate` | 画像・動画 1 件: モデルツールの選択、クレジット見積もり、生成、完了待ち、忠実度の確認、納品。 |
| `creagen-product-detail-page` | 実際の商品写真から作成する縦長の EC 商品詳細ページと、セクションごとの生成画像。 |
| `creagen-promo-video` | 9:16 のショート動画広告: 目的、絵コンテ、低コストのリファレンスシート、完成クリップ 1 本。 |
| `creagen-ugc-video` | 人物が商品を紹介し、ナレーションで語る UGC スタイルのレビュー動画。 |
| `creagen-lookbook` | バーチャル試着、多角度のスタジオカット、レタッチ済みのファッションルックブック一式。 |

スキルは指示文のみで構成されています。本プラグインにはスクリプト、フック、実行ファイルは含まれていません。スキルファイル(`SKILL.md`)は Claude が指示として読み込むため、英語のみで記述しています。Claude とはどの言語でも会話いただけます。

## 必要なもの

- Creagen アカウント。[creagen.vcat.ai](https://creagen.vcat.ai) で登録できます。
- Creagen クレジット。画像・動画の生成にはアカウントのクレジットが消費されます。スキルは、動画、一括生成、高品質ティアの前に、Claude がクレジット見積もりを提示してお客様の確認を得るよう指示しています。見積もり、残高確認、コンサルタントツール、ジャーニーでは生成クレジットは消費されません。
- 初回利用時に、コネクタの OAuth フローで Creagen にサインインしてください。

## インストール

**Claude ディレクトリから**: Claude のプラグインディレクトリで「Creagen」を検索して追加し、プラグインの Connectors タブから Creagen コネクタを接続してサインインしてください。

**Claude Code で、このリポジトリをマーケットプレイスとして追加する場合**:

```bash
/plugin marketplace add pioncorp/creagen-plugin
/plugin install creagen@creagen
```

続いて `/mcp` を実行し、`creagen` サーバーを認証してください。

**コネクタのみ(スキルなし)**: claude.ai で Settings → Connectors → Add custom connector を開き、次の URL を入力してください。

```
https://agent.vcat.ai/api/mcp/creagenOfficialMCPServer/mcp
```

## 使用例

- 「この商品写真を、すっきりした白背景のカットと、大理石カウンターの上のライフスタイルカットにしてください。」
- 「この写真とセールスポイントから、このクリームの詳細ページを作ってください。」
- 「ランナー向けに、私のスニーカーの 15 秒縦型広告を作ってください。」
- 「20 代の女性がこのコールドブリューを紹介するレビュー動画を作ってください。」
- 「この 2 着のジャケットをモデルに着せて、正面・側面・ウォーキングのカットを作ってください。」

## データとプライバシー

コネクタをご利用になると、Claude は各ツールの実行に必要な情報を Creagen に送信します。具体的には、プロンプト、アップロードまたはリンクされた画像・動画、分析を依頼された URL、ツールへの入力値です。Creagen はこれらを自社サーバーで処理し、生成リクエストを上記の AI モデル提供元に渡します。生成メディア、アップロード、メモリー、スキル、プラン、ジャーニーの進行状況はお客様の Creagen アカウントに保存され、コネクタで作成した結果は Creagen ギャラリーの「MCP」フィルターに表示されます。プラグイン自体は何も保存せず、Creagen コネクタ以外にデータを送信することはありません。

- プライバシーポリシー: https://vcat.ai/policy/privacy-policy
- 利用規約: https://vcat.ai/policy/terms-of-service

## サポート

- ヘルプセンター: https://creagen.vcat.ai/help
- メール: help@vcat.ai
- セキュリティに関する問題: [SECURITY.md](SECURITY.md) をご覧ください。

## コントリビューション

[CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## ライセンス

このリポジトリのスキル文書とマニフェストは MIT License で公開しています([LICENSE](LICENSE) を参照)。Creagen サービスのご利用には Creagen の利用規約が適用されます。
