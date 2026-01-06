"""
api.py - 名言佳句 RESTful API

基於 FastAPI 構建，提供 quotes 資料表的 CRUD 功能。
"""

import sqlite3
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import uvicorn

# --- 配置與常數 ---
DB_NAME = "quotes.db"

app = FastAPI(
    title="名言佳句 API",
    description="提供名言佳句的 CRUD 操作",
    version="1.0.0"
)


# --- Pydantic 模型 ---
class PostCreate(BaseModel):
    """建立/更新名言時的請求模型"""
    text: str = Field(..., description="名言內容", min_length=1)
    author: str = Field(..., description="作者姓名", min_length=1)
    tags: str = Field(default="", description="標籤 (以逗號分隔)")


class PostResponse(PostCreate):
    """API 回應的模型，包含 ID"""
    id: int


# --- 資料庫工具 ---
@contextmanager
def get_db_connection():
    """
    資料庫連線的 Context Manager。
    確保連線會被自動關閉 (yield pattern)。
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # 允許透過欄位名稱存取
    try:
        yield conn
    finally:
        conn.close()


# --- API 端點 ---

@app.get("/", summary="Root Endpoint")
def read_root() -> Dict[str, str]:
    return {"message": "Welcome to the Quotes API System"}


@app.get("/quotes", response_model=List[PostResponse], summary="取得所有名言")
def get_quotes():
    """從資料庫讀取所有名言資料。"""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM quotes ORDER BY id DESC")
            rows = cursor.fetchall()
            # 將 sqlite3.Row 轉為 dict
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.post("/quotes", response_model=PostResponse, status_code=status.HTTP_201_CREATED, summary="新增名言")
def create_quote(quote: PostCreate):
    """新增一筆名言至資料庫。"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO quotes (text, author, tags) VALUES (?, ?, ?)",
                (quote.text, quote.author, quote.tags)
            )
            conn.commit()
            new_id = cursor.lastrowid

            # 建立回傳物件
            return {**quote.model_dump(), "id": new_id}
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create quote: {str(e)}"
        )


@app.put("/quotes/{quote_id}", response_model=PostResponse, summary="更新名言")
def update_quote(quote_id: int, quote: PostCreate):
    """根據 ID 更新名言內容。"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE quotes SET text = ?, author = ?, tags = ? WHERE id = ?",
                (quote.text, quote.author, quote.tags, quote_id)
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Quote with ID {quote_id} not found"
                )

            return {**quote.model_dump(), "id": quote_id}
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.delete("/quotes/{quote_id}", status_code=status.HTTP_200_OK, summary="刪除名言")
def delete_quote(quote_id: int):
    """根據 ID 刪除名言。"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Quote with ID {quote_id} not found"
                )

            return {"message": "Quote deleted successfully"}
    except sqlite3.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)