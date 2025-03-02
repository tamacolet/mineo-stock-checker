import os
import time
import logging
import smtplib
import ssl
import requests
import platform
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("stock_checker.log"),
    ],
)
logger = logging.getLogger("mineo-stock-checker")


def get_product_urls():
    """環境変数からURLリストを取得"""
    urls_raw = os.getenv("PRODUCT_URLS", "")
    if not urls_raw:
        logger.error("PRODUCT_URLS 環境変数が設定されていません")
        return []

    # カンマか改行で区切られたURLを分割
    if "," in urls_raw:
        urls = [url.strip() for url in urls_raw.split(",")]
    else:
        urls = [url.strip() for url in urls_raw.split("\n") if url.strip()]

    return urls


def find_chrome_executable():
    """システムにインストールされているChromeの実行ファイルを探す"""
    system = platform.system()
    if system == "Darwin":  # macOS
        # macOSでのChromeの一般的な場所
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chrome.app/Contents/MacOS/Chrome"
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                return path
    elif system == "Windows":
        # Windowsでの一般的な場所
        chrome_paths = [
            os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"),
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                return path
    elif system == "Linux":
        # Linuxでの一般的な場所
        try:
            return subprocess.check_output(["which", "google-chrome"]).decode().strip()
        except subprocess.CalledProcessError:
            try:
                return subprocess.check_output(["which", "chrome"]).decode().strip()
            except subprocess.CalledProcessError:
                pass
    
    logger.warning(f"Chromeの実行ファイルが見つかりませんでした。システム: {system}")
    return None


def check_stock(url):
    """指定されたURLの在庫状況をチェック"""
    try:
        # Seleniumでブラウザを起動し、JavaScriptが実行された状態でHTMLを取得
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Chromeの実行ファイルのパスを取得
        chrome_path = find_chrome_executable()
        if chrome_path:
            chrome_options.binary_location = chrome_path
            logger.info(f"Chrome実行ファイルを設定: {chrome_path}")
        
        # ブラウザを起動 (Service指定なしで直接)
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # ページを読み込み、JavaScriptが実行されるのを待つ
            driver.get(url)
            # JavaScriptが実行されるのを待つ（必要に応じて調整）
            time.sleep(3)
            
            # 現在のページソースを取得
            html = driver.page_source
            
            # デバッグ用にHTMLを保存
            with open("latest_html.html", "w", encoding="utf-8") as f:
                f.write(html)
                
            soup = BeautifulSoup(html, "html.parser")
            logger.debug(f"URLからHTMLを取得しました: {url}")
        finally:
            # ブラウザを終了
            driver.quit()
        
        # 商品名を取得
        product_name = soup.select_one(".page-title h1")
        if product_name:
            product_name = product_name.text.strip()
            logger.info(f"商品名: {product_name}")
        else:
            product_name = "不明な商品"
            logger.warning(f"商品名が取得できませんでした: {url}")
            
        # 在庫状況テーブルを検索
        stock_cells = soup.select(".replace-stock-color")
        
        if not stock_cells:
            logger.warning(f"在庫情報が見つかりませんでした: {url}")
            return {
                "product_name": product_name,
                "url": url,
                "in_stock": False,
                "details": [],
                "error": "在庫情報が見つかりませんでした"
            }
        
        logger.info(f"在庫情報セルを {len(stock_cells)} 個見つけました")
        
        in_stock = False
        details = []
        
        for cell in stock_cells:
            # 色名を取得（親要素のth内）
            color_element = cell.find_previous("th")
            color_name = "不明" if not color_element else color_element.text.strip()
            
            # セルの内容をログに出力（判断根拠の表示）
            cell_text = cell.text.strip()
            logger.info(f"セル内容 ({color_name}): {cell_text}")
            
            # アイコンの有無とクラスを確認
            icon = cell.find("i")
            icon_class = None
            if icon:
                icon_class = icon.get('class')
                logger.info(f"  - アイコンクラス: {icon_class}")
            
            # data-stock-status属性の値を取得
            data_stock_status = cell.get('data-stock-status')
            if data_stock_status:
                logger.info(f"  - data-stock-status: {data_stock_status}")
            
            # ------ 在庫判断ロジック（優先順位順） ------
            # 1. data-stock-statusの値による判断（サイトの仕様に基づく）
            #    - data-stock-status="2" → 在庫なし
            #    - data-stock-status="1" → 在庫あり
            # 2. テキストに「在庫なし」または「入荷待ち」がある場合は在庫なし
            # 3. テキストがあり、それが「在庫なし」でない場合は在庫あり
            # 4. アイコンの存在だけでは在庫ありと判断しない（JavaScriptで動的に変更される可能性があるため）
            
            if data_stock_status == "2":
                status = "在庫なし"
                logger.info(f"  - 判断根拠: data-stock-status=\"2\"（在庫なし）")
            elif data_stock_status == "1":
                status = "在庫あり"
                in_stock = True
                logger.info(f"  - 判断根拠: data-stock-status=\"1\"（在庫あり）")
            elif "在庫なし" in cell_text or "入荷待ち" in cell_text:
                status = "在庫なし"
                logger.info(f"  - 判断根拠: テキストに「在庫なし」または「入荷待ち」を含む")
            elif cell_text and "在庫なし" not in cell_text and "入荷待ち" not in cell_text:
                # テキストがあり、それが「在庫なし」でない場合は在庫あり
                status = "在庫あり"
                in_stock = True
                logger.info(f"  - 判断根拠: テキストが存在し、「在庫なし」や「入荷待ち」を含まない")
            elif icon and icon_class and 'fa-circle' in icon_class:
                # アイコンだけでは判断できないが、調査のためログに残す
                logger.warning(f"  - 注意: アイコン「fa-circle」の存在のみで在庫判断はできません。サイトが動的に更新されている可能性があります。")
                status = "判断不能（要確認）"
            else:
                status = "状態不明"
                logger.info(f"  - 判断根拠: 既知のパターンに一致しない")
            
            details.append({
                "color": color_name,
                "status": status
            })
        
        result = {
            "product_name": product_name,
            "url": url,
            "in_stock": in_stock,
            "details": details,
            "error": None
        }
        
        return result
        
    except Exception as e:
        logger.error(f"在庫チェック中にエラーが発生しました: {url} - {str(e)}")
        return {
            "product_name": url,
            "url": url,
            "in_stock": False,
            "details": [],
            "error": str(e)
        }


def send_email(in_stock_products):
    """在庫のある商品についてメール通知を送信"""
    if not in_stock_products:
        logger.info("在庫のある商品はありません。メール送信をスキップします。")
        return
    
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    
    if not all([email_user, email_pass, recipient_email]):
        logger.error("メール送信に必要な環境変数が設定されていません")
        return
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"【在庫あり】mineo商品在庫通知 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        message["From"] = email_user
        message["To"] = recipient_email
        
        # HTML形式のメール本文を作成
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .stock-available {{ color: green; font-weight: bold; }}
                .stock-unavailable {{ color: red; }}
            </style>
        </head>
        <body>
            <h2>mineo商品在庫通知</h2>
            <p>以下の商品に在庫があります：</p>
            
            <table>
                <tr>
                    <th>商品名</th>
                    <th>カラー</th>
                    <th>在庫状況</th>
                </tr>
        """
        
        for product in in_stock_products:
            for detail in product["details"]:
                if detail["status"] == "在庫あり":
                    status_class = "stock-available"
                    status_text = "在庫あり"
                else:
                    status_class = "stock-unavailable"
                    status_text = detail["status"]
                    
                html += f"""
                <tr>
                    <td><a href="{product['url']}">{product['product_name']}</a></td>
                    <td>{detail['color']}</td>
                    <td class="{status_class}">{status_text}</td>
                </tr>
                """
        
        html += """
            </table>
            <p>商品ページにアクセスするには、商品名をクリックしてください。</p>
        </body>
        </html>
        """
        
        text_part = MIMEText("在庫のある商品が見つかりました。詳細はHTMLメールをご確認ください。", "plain")
        html_part = MIMEText(html, "html")
        
        message.attach(text_part)
        message.attach(html_part)
        
        # SMTPサーバーに接続してメール送信
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(email_user, email_pass)
            server.sendmail(email_user, recipient_email, message.as_string())
            
        logger.info(f"在庫通知メールを送信しました: {recipient_email}")
        
    except Exception as e:
        logger.error(f"メール送信中にエラーが発生しました: {str(e)}")


def main():
    """メイン処理"""
    logger.info("mineo在庫チェッカー実行開始")
    
    urls = get_product_urls()
    if not urls:
        logger.error("チェックする商品URLがありません")
        return
    
    logger.info(f"{len(urls)}個の商品URLをチェックします")
    
    in_stock_products = []
    all_results = []
    
    for url in urls:
        logger.info(f"URLをチェック中: {url}")
        result = check_stock(url)
        all_results.append(result)
        
        if result["in_stock"]:
            in_stock_products.append(result)
            logger.info(f"在庫あり: {result['product_name']}")
            
            # 在庫ありの詳細をログに出力
            for detail in result["details"]:
                if detail["status"] == "在庫あり":
                    logger.info(f"  - {detail['color']}: {detail['status']}")
    
    # 在庫結果の要約をログに出力
    logger.info(f"チェック完了: 合計{len(urls)}商品中、{len(in_stock_products)}商品で在庫あり")
    
    # 在庫がある場合はメール送信
    if in_stock_products:
        send_email(in_stock_products)
    
    logger.info("mineo在庫チェッカー実行終了")


if __name__ == "__main__":
    main() 