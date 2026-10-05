# 唐詩小旅行（Larch 互動教材）

給小學三年級的唐詩互動教材，做在 [Larch](https://larch.ink) 上。阿禾和小樂兩個小朋友掉進詩的世界，跟著劇情認生字、跟著念、背全詩。

第一首：〈過故人莊〉（孟浩然）。試玩：<https://larch.ink/play/hzfNrl_bj6cl647p35_38tw1tlUoK_ePe81Vmg>

- 23 個生字，其中 12 個要答題；答錯時角色換個說法解釋，再回來重答。
- 每一聯「跟著念」，逐字點亮，每個字都能點來聽。
- 最後把四張圖排成詩的順序，先複習答錯過的字，再闖三關背誦。
- 唐代田家的畫面照考證畫：黍是黃色小米、郭是外城、場圃是打穀場和菜園。

教學骨架（生字卡、四張圖背誦法）參考自 [doggy8088/TangPoetry-guo-guren-zhuang](https://github.com/doggy8088/TangPoetry-guo-guren-zhuang)；本 repo 的劇本、角色、美術、配音皆為另行創作。

## 目錄

| 路徑 | 內容 |
|---|---|
| `canon/系列角色.md`、`canon/角色/` | 系列主角設定與四個角色的定錨圖 |
| `poems/guo-guren-zhuang/script.md` | 劇本（格式寫在 `src/script.py` 開頭） |
| `poems/guo-guren-zhuang/vocab.json` | 23 個生字：注音、解釋、是否出題、配音替身字 |
| `poems/guo-guren-zhuang/考證.md` | 唐代田家與注音的出處 |
| `poems/guo-guren-zhuang/art/`、`audio/` | 背景、CG、生字圖、立繪；生字與跟念音檔 |
| `src/plugin/` | 自製插件 tangshi-kit：生字卡、跟著念、四張圖排順序、背誦闖關 |
| `src/build.py` | 讀劇本與生字資料，組出 `dist/project.json` |
| `src/push.py` | 推上 Larch：快照、上傳、整包 PUT、讀回比對 |
| `docs/specs/`、`docs/plans/` | 設計規格與實作計劃 |

## 指令

    python3 src/build.py                                   # 產出 dist/project.json
    python3 ~/larch-preview/serve.py dist/project.json     # 本機播放
    python3 tests/check_static.py                          # 靜態檢查
    node tests/cards.mjs [vocab|follow|order|recite]       # 單卡測試
    node tests/play_all.mjs [right|wrong]                  # 全路徑試玩（全對、每字先錯一次）
    ONLINE=<試玩網址> node tests/play_all.mjs right         # 對線上版跑一次
    python3 src/art_jobs.py [bg|vocab|char|cg]             # 產圖（本機 codex）
    python3 src/standees.py                                # 立繪去背、統一畫布
    python3 src/vocab_audio.py                             # 生字與跟念音檔（larch-tts-bridge）
    python3 src/push.py "改了什麼"                          # 推上 Larch（發佈要作者在網頁按）

下一首詩：在 `poems/` 開新資料夾，放 `script.md`、`vocab.json`、`考證.md`，插件與建置不用改。

## 授權

- 程式碼：MIT，見 `LICENSE`。
- 角色、劇本、美術、配音：CC BY-NC 4.0（非商業可分享改作，需署名；商業使用請洽林亞澤）。
