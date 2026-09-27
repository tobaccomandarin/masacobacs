# Claude — Motion Reel (15 s)

`out/claude_motion_reel.mp4` は、映像・音楽・効果音をすべてコードで生成した15秒の縦長ショートリールです。

- 1080×1920、60fps、H.264 High / AAC 48kHz ステレオ(iPhoneでそのまま再生できる形式)
- 128 BPM、8小節ちょうど(1小節 = 1.875秒)。最後のフレームが最初のフレームにつながるため、ループ再生で継ぎ目が出ません。

| 小節 | 章 | 見せている原則 |
|---|---|---|
| 1 | SQUASH & STRETCH | バウンドするボール、モーションパス、着地の波紋 |
| 2 | KINETIC TYPE | マスク+スタッガーで出現する字幅合わせのタイポグラフィ |
| 3 | EASING | グラフエディタ上で linear から cubic-bezier(0.16, 1, 0.3, 1) へ変化、オニオンスキン |
| 4 | STAGGER | 48個のセルが中心から波紋状に形を変える |
| 5 | IMPACT | ドロップ。フラッシュ、3Dドットのトンネル、グリッチ文字 |
| 6 | PARALLAX | 奥行きの異なる文字列のマーキーと、円周上を回る文字のバッジ |
| 7 | CONSTRUCTION | 作図ガイドから放射状のマークが組み上がる |
| 8 | SIGNATURE | エンドカードのあと、アイリスで冒頭の点に戻る |

## 再生成

```
pip install numpy scipy pycairo fonttools imageio-ffmpeg pillow
python3 make.py
```

- `lib.py`:タイムライン、イージング、フォントのアウトラインを使った文字描画
- `scenes.py`:8つのシーン、HUD、カメラシェイク
- `render.py`:8サンプルのモーションブラー(180°シャッター、カットをまたがない)、色収差、ビネット、グレイン
- `audio.py`:ドラム、ベース、コード、アルペジオ、効果音をnumpyで合成(サンプル素材は不使用)
- `make.py`:並列レンダリングとエンコード

フォントは Inter、JetBrains Mono、Instrument Serif、Noto Sans JP(いずれも SIL Open Font License 1.1、`fonts/` にライセンス同梱)です。
