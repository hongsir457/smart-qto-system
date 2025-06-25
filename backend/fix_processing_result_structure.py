#!/usr/bin/env python3
"""
批量修复drawings.processing_result结构，补全AnalysisResultsResponse所需字段
"""
from app.database import get_db
from app.models.drawing import Drawing
import json

def fix_processing_result_structure():
    session = next(get_db())
    drawings = session.query(Drawing).all()
    fixed = 0
    for drawing in drawings:
        pr = drawing.processing_result
        if not pr:
            continue
        if isinstance(pr, str):
            try:
                pr = json.loads(pr)
            except Exception:
                continue
        changed = False
        # 补全AnalysisResultsResponse字段
        for key, default in [
            ("analysis_type", "stage_two"),
            ("has_ai_analysis", False),
            ("components", []),
            ("analysis_summary", {}),
            ("quality_assessment", {}),
            ("recommendations", []),
            ("statistics", {}),
        ]:
            if key not in pr:
                pr[key] = default
                changed = True
        # llm_analysis 可为None
        if "llm_analysis" not in pr:
            pr["llm_analysis"] = None
            changed = True
        if changed:
            drawing.processing_result = pr
            fixed += 1
    session.commit()
    print(f"已修复 {fixed} 条记录")
    session.close()

if __name__ == "__main__":
    fix_processing_result_structure() 