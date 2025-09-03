from PyPDF2 import PdfReader, PdfWriter

# 读取原始 PDF
reader = PdfReader("test.pdf")
writer = PdfWriter()

# 合并所有页面为单页
for page in reader.pages:
    writer.add_page(page)

# 调整页面大小（例如设置为 A4 横向）
from PyPDF2.generic import RectangleObject
for page in writer.pages:
    page.mediabox = RectangleObject([0, 0, 595.28, 841.89])  # A4 尺寸（mm）

# 保存为新 PDF
with open("output.pdf", "wb") as f:
    writer.write(f)
