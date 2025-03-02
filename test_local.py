import os
import logging
from bs4 import BeautifulSoup
from stock_checker import send_email

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("mineo-stock-checker-test")

def check_stock_from_file(file_path, url="https://example.com"):
    """ローカルのHTMLファイルから在庫状況をチェック"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        soup = BeautifulSoup(html_content, "html.parser")
        logger.debug(f"ファイルからHTMLを読み込みました: {file_path}")
        
        # 商品名を取得
        product_name = soup.select_one(".page-title h1")
        if product_name:
            product_name = product_name.text.strip()
            logger.info(f"商品名: {product_name}")
        else:
            product_name = "不明な商品"
            logger.warning(f"商品名が取得できませんでした: {file_path}")
            
        # 在庫状況テーブルを検索
        stock_cells = soup.select(".replace-stock-color")
        
        if not stock_cells:
            logger.warning(f"在庫情報が見つかりませんでした: {file_path}")
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
            # 1. テキストに「在庫なし」または「入荷待ち」がある場合は在庫なし
            # 2. data-stock-statusの値による判断（サイトの仕様に基づく）
            #    - data-stock-status="2" → 在庫なし
            #    - data-stock-status="1" → 在庫あり
            # 3. テキストがあり、それが「在庫なし」でない場合は在庫あり
            # 4. アイコンの存在だけでは在庫ありと判断しない（JavaScriptで動的に変更される可能性があるため）
            
            if "在庫なし" in cell_text or "入荷待ち" in cell_text:
                status = "在庫なし"
                logger.info(f"  - 判断根拠: テキストに「在庫なし」または「入荷待ち」を含む")
            elif data_stock_status == "2":
                status = "在庫なし"
                logger.info(f"  - 判断根拠: data-stock-status=\"2\"（在庫なし）")
            elif data_stock_status == "1":
                status = "在庫あり"
                in_stock = True
                logger.info(f"  - 判断根拠: data-stock-status=\"1\"（在庫あり）")
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
        logger.error(f"在庫チェック中にエラーが発生しました: {file_path} - {str(e)}")
        return {
            "product_name": file_path,
            "url": url,
            "in_stock": False,
            "details": [],
            "error": str(e)
        }

def main():
    """テスト実行"""
    logger.info("mineo在庫チェッカーテスト実行開始")
    
    # テスト対象のHTMLファイル
    test_files = [
        {
            "file": "https___mineo_jp_device_smartphone_motorola_edge_40_neo_.html",
            "url": "https://mineo.jp/device/smartphone/motorola-edge-40-neo/"
        },
        {
            "file": "https___mineo_jp_device_smartphone_aquos_sense9_8gb_256gb_.html",
            "url": "https://mineo.jp/device/smartphone/aquos-sense9/"
        }
    ]
    
    in_stock_products = []
    all_results = []
    
    for test in test_files:
        file_path = test["file"]
        url = test["url"]
        
        logger.info(f"ファイルをチェック中: {file_path}")
        result = check_stock_from_file(file_path, url)
        all_results.append(result)
        
        logger.info(f"商品名: {result['product_name']}")
        logger.info(f"在庫あり: {result['in_stock']}")
        
        for detail in result["details"]:
            logger.info(f"  - {detail['color']}: {detail['status']}")
        
        if result["in_stock"]:
            in_stock_products.append(result)
    
    # 在庫結果の要約をログに出力
    logger.info(f"チェック完了: 合計{len(test_files)}商品中、{len(in_stock_products)}商品で在庫あり")
    
    # 在庫情報をコンソールに表示
    if in_stock_products:
        logger.info("在庫のある商品:")
        for product in in_stock_products:
            logger.info(f"- {product['product_name']}")
            for detail in product["details"]:
                if detail["status"] == "在庫あり":
                    logger.info(f"  - {detail['color']}: {detail['status']}")
    
    # メール送信をテストする場合は環境変数を設定して以下のコメントを解除
    # if in_stock_products and os.getenv("EMAIL_USER") and os.getenv("EMAIL_PASS") and os.getenv("RECIPIENT_EMAIL"):
    #     send_email(in_stock_products)
    
    logger.info("mineo在庫チェッカーテスト実行終了")

if __name__ == "__main__":
    main() 