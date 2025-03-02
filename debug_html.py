import requests
from bs4 import BeautifulSoup
import logging
import sys
import json

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('html-debug')

def get_and_analyze_html(url):
    """URLからHTMLを取得し、在庫状況関連の要素を分析"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        logger.info(f"URLからHTMLを取得中: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"HTTPステータス: {response.status_code}")
        logger.info(f"レスポンスヘッダー: {dict(response.headers)}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 在庫状況セクションを探す
        stock_section = soup.select_one(".device-stock-container")
        if stock_section:
            logger.info("在庫状況セクションの全HTML:")
            logger.info(stock_section.prettify())
            
            # 在庫状況テーブルの各セルを確認
            stock_cells = stock_section.select(".replace-stock-color")
            logger.info(f"在庫状況セル数: {len(stock_cells)}")
            
            for i, cell in enumerate(stock_cells):
                logger.info(f"セル {i+1} 詳細:")
                logger.info(f"  テキスト内容: [{cell.text.strip()}]")
                logger.info(f"  HTML: {cell}")
                logger.info(f"  属性: {cell.attrs}")
                
                # アイコン要素があれば詳細表示
                icons = cell.find_all("i")
                logger.info(f"  アイコン要素数: {len(icons)}")
                for j, icon in enumerate(icons):
                    logger.info(f"    アイコン {j+1}: {icon}")
                    logger.info(f"    アイコン {j+1} 属性: {icon.attrs}")
        else:
            logger.warning("在庫状況セクションが見つかりませんでした")
        
        # HTMLをファイルに保存（オプション）
        with open("latest_html.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        logger.info("完全なHTMLを 'latest_html.html' に保存しました")
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        
if __name__ == "__main__":
    url = "https://mineo.jp/device/smartphone/motorola-edge-40-neo/"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    get_and_analyze_html(url) 