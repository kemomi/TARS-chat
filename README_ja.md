
# Stack-chan

[![Build Stack-chan Firmware](https://github.com/stack-chan/stack-chan/actions/workflows/build.yml/badge.svg)](https://github.com/stack-chan/stack-chan/actions/workflows/build.yml)
[![Discord server invitation](https://img.shields.io/badge/Discord-%E6%9C%8D%E5%8B%99%E5%99%A8%E3%81%AB%E5%8F%82%E5%8A%A0-5865F2?logo=discord&logoColor=white)](https://discord.gg/eGhd9adnBm)

[日本語](./README_ja.md) | [English](./README.md) | [中文](./README_cn.md)

![stackchan](./docs/images/stackchan.gif)

Stack-chanは、JavaScriptで駆動されるM5Stack内蔵の超かわいいロボットです。

*   **動画:** https://youtu.be/fZb_mF08xV0
*   **公式ハッシュタグ:** [`#stackchan` | `#ｽﾀｯｸﾁｬﾝ` (JP)](https://twitter.com/search?q=%23stackchan%20OR%20%23%EF%BD%BD%EF%BE%80%EF%BD%AF%EF%BD%B8%EF%BE%81%EF%BD%AC%EF%BE%9D)

## 機能紹介

*   :neutral_face:     可愛い表情を表示
*   :smile:            感情表現 (Happy, Angry, Sad など)
*   :smiley_cat:       表情のカスタマイズ
*   :eyes:             視線操作 (Glance/stare/gaze)
*   :speech_balloon:   発言
*   :bulb:             M5Units 拡張対応
*   :cyclone:          Serial(TTL)/PWM サーボ駆動
*   :game_die:         オリジナルアプリケーション開発

## コンテンツ

このリポジトリには、ロボットを構成するすべてのコンポーネントが含まれています。

*   **firmware** : ファームウェアのソースコード。
*   **case** : ケースのステレオリソグラフィ (STL) データ。
*   **schematics** : 回路図および基板レイアウトデータ。

## 導入方法

### 1. 基板の組立
*   [schematics/README.md](./schematics/README.md) および [case/README.md](./case/README.md) を参照してください。
*   または：プリアセンブリモジュールを入手 (近日発売予定)

### 2. M5Stack へのファームウェア書き込み
*   [firmware/README.md](./firmware/README.md) を参照してください。

## 開発

コントリビューター向けのセットアップやプルリクエストの期待事項については、[CONTRIBUTING.md](./CONTRIBUTING.md) をご覧ください。

典型的なファームウェア開発ワークフロー：
```bash
cd firmware
npm run setup
npm run doctor
npm run test
npm run build
```

`web/flash` および `web/schematics` 以下のWebアセットは、GitHub Actions により `gh-pages` ブランチから公開されます。これらは手動でメンテナンスするソースファイルではなく、デプロイメント出力物として扱ってください。

## 開発ロードマップ

*   [docs/ROADMAP.md](./docs/ROADMAP.md)

## コントリビューション

**機能要望やバグ報告を大募集しています！** [issues](https://github.com/stack-chan/stack-chan/issues) ページから投稿してください。

**スポンサーになりたいですか？** 大変光栄です。私の [スポンサーページ](httpsUp://github.com/sponsors/meganetaaan/) をご覧ください。

## ライセンス

このリポジトリのリソースは Apache 2.0 ライセンスの下に配布されています。
[License](./LICENSE) を参照してください。

## 引用情報 (BibTeX)

```bibtex
@misc{stackchan,
  author       = {Shinya Ishikawa and the Stack-chan community},
  title        = {Stack-chan: A JavaScript-driven Super-kawaii Robot},
  year         = {2021},
  howpublished = {\url{https://github.com/stack-chan/stack-chan}},
  note        Up = {Open-source hardware and software.},
}
```
```

---