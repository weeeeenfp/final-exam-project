"""
pacho.py - 動態名言佳句爬蟲

此模組負責使用 Selenium 抓取 http://quotes.toscrape.com/js/ 的內容，
並將資料儲存至 SQLite 資料庫中。
"""

import sqlite3
import time
import logging
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# 設定日誌記錄 (Logging) 取代 print，更專業
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DB_NAME = "quotes.db"
TARGET_URL = "http://quotes.toscrape.com/js/"


def init_db() -> None:
    """初始化資料庫，若表格不存在則建立。"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    author TEXT NOT NULL,
                    tags TEXT
                )
            ''')
            conn.commit()
        logging.info(f"資料庫 {DB_NAME} 初始化/檢查完成。")
    except sqlite3.Error as e:
        logging.error(f"資料庫初始化失敗: {e}")


def save_quote(text: str, author: str, tags: str) -> None:
    """
    將單筆名言存入資料庫。

    Args:
        text (str): 名言內容
        author (str): 作者
        tags (str): 標籤字串
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO quotes (text, author, tags) VALUES (?, ?, ?)",
                (text, author, tags)
            )
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"儲存資料時發生錯誤: {e}")


def get_driver() -> webdriver.Chrome:
    """設定並回傳 Chrome WebDriver 實例。"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 無頭模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # 隱藏 Selenium 的一些無用 Log
    chrome_options.add_argument("--log-level=3")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def scrape_quotes() -> None:
    """執行爬蟲主邏輯：瀏覽網頁、解析內容並換頁。"""
    logging.info("正在啟動 Selenium 爬蟲...")
    driver = get_driver()

    try:
        driver.get(TARGET_URL)

        # 爬取前 5 頁
        for page in range(1, 6):
            logging.info(f"正在處理第 {page} 頁...")

            try:
                # 等待名言區塊載入 (最多等待 10 秒)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "quote"))
                )

                quote_elements = driver.find_elements(By.CLASS_NAME, "quote")

                if not quote_elements:
                    logging.warning(f"第 {page} 頁未發現名言區塊。")
                    break

                for element in quote_elements:
                    try:
                        text = element.find_element(By.CLASS_NAME, "text").text
                        author = element.find_element(By.CLASS_NAME, "author").text

                        tag_elements = element.find_elements(By.CLASS_NAME, "tag")
                        tags = ",".join([t.text for t in tag_elements])

                        save_quote(text, author, tags)
                    except NoSuchElementException as e:
                        logging.warning(f"解析元素時發生錯誤 (略過此筆): {e}")

                logging.info(f"第 {page} 頁處理完成，共 {len(quote_elements)} 筆。")

                # 處理換頁
                if page < 5:
                    try:
                        next_btn = driver.find_element(By.CSS_SELECTOR, "li.next > a")
                        # 使用 JS 點擊較穩定
                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(1)  # 稍微緩衝，等待 JS 動畫
                    except NoSuchElementException:
                        logging.info("已無下一頁，停止爬取。")
                        break

            except TimeoutException:
                logging.error(f"載入第 {page} 頁超時。")
                break

    except WebDriverException as e:
        logging.critical(f"WebDriver 發生嚴重錯誤: {e}")
    finally:
        driver.quit()
        logging.info("爬蟲結束，瀏覽器已關閉。")


if __name__ == "__main__":
    init_db()
    scrape_quotes()