# mineo 在庫チェッカー

mineo の商品ページから在庫状況を自動的にチェックし、在庫がある場合にメールで通知するツールです。GitHub Actions を使用して 5 分ごとに実行されます。

## 機能

- mineo ウェブサイトの商品ページから在庫状況を自動的にスクレイピング
- JavaScript 実行後のページ状態を取得して data-stock-status 属性で在庫状況を正確に判断
- 在庫がある場合、Gmail を使用して通知メールを送信
- GitHub Actions で 5 分ごとに自動実行
- 複数の商品 URL を同時に監視

## セットアップ方法

### 1. このリポジトリをフォークする

GitHub アカウントでこのリポジトリをフォークします。

### 2. 必要なライブラリのインストール

```bash
pip install -r requirements.txt
```

以下のライブラリが必要です：

- requests
- beautifulsoup4
- selenium
- webdriver-manager

### 3. Chrome ドライバーの準備

スクリプトは自動的に webdriver-manager を使用して Chrome ドライバーをインストールします。Chrome/Chromium ブラウザがインストールされていることを確認してください。

### 4. GitHub Secrets の設定

リポジトリの「Settings」→「Secrets and variables」→「Actions」で以下の Secret を設定します：

| Secret 名       | 説明                                         | 例                     |
| --------------- | -------------------------------------------- | ---------------------- |
| EMAIL_USER      | 通知メール送信用の Gmail アドレス            | example@gmail.com      |
| EMAIL_PASS      | メール送信用のアプリパスワード               | abcdefghijklmnop       |
| RECIPIENT_EMAIL | 通知の送信先メールアドレス                   | your-email@example.com |
| PRODUCT_URLS    | 監視する商品 URL（カンマまたは改行で区切る） | 下記参照               |

#### PRODUCT_URLS の設定例

以下のように、カンマまたは改行で区切って複数の URL を指定できます：

```
# カンマ区切りの例
https://mineo.jp/device/smartphone/motorola-edge-40-neo/,https://mineo.jp/device/smartphone/aquos-sense9/

# 改行区切りの例
https://mineo.jp/device/smartphone/motorola-edge-40-neo/
https://mineo.jp/device/smartphone/aquos-sense9/
https://mineo.jp/device/smartphone/pixel-7a/
```

### 5. Gmail アプリパスワードの取得方法

1. Google アカウントにログイン
2. セキュリティ設定に移動
3. 2 段階認証を有効にする
4. 「アプリパスワード」を生成する
5. アプリを「メール」、デバイスを「その他」として名前を入力
6. 生成されたパスワードを `EMAIL_PASS` Secret に設定

## 手動実行

GitHub Actions のワークフローページから「Run workflow」ボタンをクリックすることで、スケジュールを待たずに手動で実行できます。

## トラブルシューティング

### メールが送信されない

- Gmail 側の設定を確認してください
- アプリパスワードが正しく設定されているか確認してください
- 「安全性の低いアプリ」のアクセスが許可されているか確認してください

### 在庫チェックがうまく動作しない

- 監視対象の URL が正しいか確認してください
- URL が mineo の商品ページであるか確認してください
- mineo のウェブサイト構造が変更された場合は、`stock_checker.py`を更新する必要があります
- Chrome ブラウザがインストールされているか確認してください

### GitHub Actions で実行する場合

GitHub Actions で実行する場合は、ワークフローファイル内で Chrome をインストールするステップを追加する必要があります。

```yaml
- name: Install Chrome
  run: |
    sudo apt-get update
    sudo apt-get install -y wget gnupg
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
    sudo apt-get update
    sudo apt-get install -y google-chrome-stable
```

## ライセンス

MIT
