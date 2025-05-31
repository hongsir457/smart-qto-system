import os
from pathlib import Path
from typing import List
from .dwg_processor import DWGProcessor
from PIL import Image

class DWGToPDFConverter:
    def __init__(self):
        self.processor = DWGProcessor()

    def dwg_to_pdf(self, dwg_path: str, output_pdf: str) -> bool:
        # 1. 多图框检测
        result = self.processor.process_multi_sheets(dwg_path)
        if not result.get("success"):
            print("DWG多图框检测失败")
            return False

        drawings = result.get("drawings", [])
        images = []
        for drawing in drawings:
            img_path = drawing.get("frame_image")
            if img_path and os.path.exists(img_path):
                images.append(Image.open(img_path).convert("RGB"))

        if not images:
            print("未生成任何图框图片")
            return False

        # 2. 合成PDF
        images[0].save(output_pdf, save_all=True, append_images=images[1:])
        print(f"PDF已生成：{output_pdf}")
        return True
