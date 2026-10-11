# -*- coding: utf-8 -*-
"""文本与表格导入辅助。

- load_text：从 txt/docx 提取纯文字（保留换行，不含表格与样式）。
  docx 的加粗、字号等排版无法带入纯文本框，段落结构保留。
- load_table_rows：从 Excel/CSV 读为行列表，按表头列数对齐
  （少补空、多截断、空行跳过）。
"""
import pandas as pd


def load_text(path):
    low = str(path).lower()
    if low.endswith(".docx"):
        from docx import Document
        doc = Document(path)
        lines = [p.text for p in doc.paragraphs]
        return "\n".join(ln for ln in lines if ln.strip())
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError("文本文件编码无法识别")


def load_table_rows(path, ncols):
    from .importer import load_table
    df = load_table(path)
    rows = []
    for _, row in df.iterrows():
        vals = ["" if pd.isna(v) else str(v).strip() for v in row]
        vals = (vals + [""] * ncols)[:ncols]
        if any(vals):
            rows.append(vals)
    return rows
