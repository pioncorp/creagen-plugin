[English](README.md) · **한국어** · [日本語](README.ja.md)

# Creagen for Claude

Creagen 은 PION Corporation 이 만든 상품 판매자·브랜드 팀용 마케팅 크리에이티브 도구입니다. 이 플러그인은 Claude 를 Creagen 계정에 연결하고, 마케팅·상품 디자인 에셋 제작용 워크플로 스킬을 더합니다: 상품 사진 생성·편집, 이커머스 상세페이지, 숏폼 상품 광고, UGC 스타일 리뷰 영상, 패션 룩북.

플러그인은 Creagen 이 호스팅하는 커넥터를 통해 AI 이미지·영상 생성 모델(예: Google Nano Banana·Veo, OpenAI GPT Image, Kling, Seedance)을 사용합니다. 생성은 Creagen 서버에서 실행되며 계정의 Creagen 크레딧이 차감됩니다.

## 구성

- **Creagen 커넥터** (`.mcp.json`): 원격 MCP 서버 `https://agent.vcat.ai/api/mcp/creagenOfficialMCPServer/mcp`. 생성 도구(모델별 1도구), 크레딧 견적·잔액, 파일 업로드, 진행·미디어 위젯, 저장된 Creagen 메모리·채팅방, 전문가 컨설턴트 도구(포토그래퍼, 카피라이터, 시나리오 작가, 배너·캐러셀·상세페이지·UGC 디자이너), 결과 검수, 가이드 여정을 제공합니다.
- **스킬**: 자주 쓰는 마케팅 산출물을 만들 때 위 도구를 어떻게 조합할지 설명하는 Markdown 지시문입니다.

| 스킬 | 용도 |
|---|---|
| `creagen-generate` | 이미지·영상 1건: 모델 도구 선택, 크레딧 견적, 생성, 완료 대기, 충실도 확인, 전달. |
| `creagen-product-detail-page` | 실제 상품 사진으로 만드는 긴 이커머스 상세페이지와 섹션별 생성 이미지. |
| `creagen-promo-video` | 9:16 숏폼 상품 광고: 목표, 스토리보드, 저비용 레퍼런스 시트, 최종 클립 1개. |
| `creagen-ugc-video` | 인물이 상품을 소개하고 말하는 UGC 스타일 리뷰 영상. |
| `creagen-lookbook` | 가상 피팅, 다각도 스튜디오 컷, 리터칭한 패션 룩북 세트. |

스킬은 지시문뿐입니다. 플러그인에는 스크립트·훅·실행 파일이 없습니다. 스킬 파일(`SKILL.md`)은 Claude 가 지시문으로 읽기 때문에 영어로만 작성합니다. Claude 와의 대화는 어떤 언어로 해도 됩니다.

## 필요 조건

- Creagen 계정. [creagen.vcat.ai](https://creagen.vcat.ai) 에서 가입합니다.
- Creagen 크레딧. 이미지·영상 생성은 계정 크레딧을 차감합니다. 스킬은 영상·일괄 생성·고품질 티어 전에 Claude 가 크레딧 견적을 보여주고 사용자 확인을 받도록 합니다. 견적, 잔액 조회, 컨설턴트 도구, 여정은 생성 크레딧을 쓰지 않습니다.
- 처음 사용할 때 커넥터의 OAuth 흐름으로 Creagen 에 로그인합니다.

## 설치

**Claude 디렉터리에서**: Claude 플러그인 디렉터리에서 "Creagen" 을 검색해 추가하고, 플러그인의 Connectors 탭에서 Creagen 커넥터를 연결해 로그인합니다.

**Claude Code 에서, 이 레포를 마켓플레이스로**:

```bash
/plugin marketplace add pioncorp/creagen-plugin
/plugin install creagen@creagen
```

이어서 `/mcp` 로 `creagen` 서버를 인증합니다.

**커넥터만 (스킬 없이)**: claude.ai 에서 Settings → Connectors → Add custom connector 로 이동해 다음 주소를 입력합니다:

```
https://agent.vcat.ai/api/mcp/creagenOfficialMCPServer/mcp
```

## 예시

- "이 상품 사진을 깔끔한 흰 배경 컷과 대리석 카운터 위 라이프스타일 컷으로 만들어줘."
- "이 사진과 셀링 포인트로 이 크림 상세페이지 만들어줘."
- "러너를 겨냥한 내 운동화 15초 세로형 광고 만들어줘."
- "20대 여성이 이 콜드브루를 소개하는 리뷰 영상 만들어줘."
- "이 재킷 두 벌을 모델에게 입혀서 정면·측면·워킹 컷 뽑아줘."

## 데이터와 개인정보

커넥터를 사용하면 Claude 는 각 도구 실행에 필요한 정보를 Creagen 에 보냅니다: 프롬프트, 업로드하거나 링크한 이미지·영상, 분석을 요청한 URL, 도구 입력값. Creagen 은 이를 자체 서버에서 처리하고 생성 요청을 위에 적은 AI 모델 제공사에 전달합니다. 생성 미디어, 업로드, 메모리, 스킬, 플랜, 여정 진행 상황은 Creagen 계정에 저장되며, 커넥터로 만든 결과는 Creagen 갤러리의 "MCP" 필터에 표시됩니다. 플러그인 자체는 아무것도 저장하지 않고 Creagen 커넥터 외에는 데이터를 보내지 않습니다.

- 개인정보 처리방침: https://vcat.ai/policy/privacy-policy
- 이용약관: https://vcat.ai/policy/terms-of-service

## 지원

- 도움말 센터: https://creagen.vcat.ai/help
- 이메일: help@vcat.ai
- 보안 문제: [SECURITY.md](SECURITY.md) 참고.

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md) 참고.

## 라이선스

이 레포의 스킬 문서와 매니페스트는 MIT License 로 공개됩니다([LICENSE](LICENSE) 참고). Creagen 서비스 이용은 Creagen 이용약관을 따릅니다.
