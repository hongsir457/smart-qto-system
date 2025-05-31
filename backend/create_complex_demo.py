import cv2
import numpy as np
import math

# 创建一个更复杂的建筑图纸
img = np.ones((800, 1000, 3), dtype=np.uint8) * 255
font = cv2.FONT_HERSHEY_SIMPLEX

# 添加标题和图纸信息
cv2.putText(img, 'ARCHITECTURAL FLOOR PLAN', (300, 40), font, 1.0, (0, 0, 0), 2)
cv2.putText(img, 'Project: Residential Building A', (50, 70), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Scale: 1:100', (50, 90), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Drawing No: A-001', (700, 70), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Date: 2024-01-15', (700, 90), font, 0.6, (0, 0, 0), 1)

# 绘制外墙
cv2.rectangle(img, (100, 120), (900, 650), (0, 0, 0), 3)

# 绘制内墙
cv2.line(img, (350, 120), (350, 650), (0, 0, 0), 2)  # 垂直分隔墙
cv2.line(img, (650, 120), (650, 650), (0, 0, 0), 2)  # 垂直分隔墙
cv2.line(img, (100, 350), (900, 350), (0, 0, 0), 2)  # 水平分隔墙
cv2.line(img, (100, 500), (650, 500), (0, 0, 0), 2)  # 部分水平墙

# 绘制门
def draw_door(img, x, y, width, height, direction='right'):
    if direction == 'right':
        cv2.line(img, (x, y), (x + width, y), (255, 255, 255), 3)
        cv2.ellipse(img, (x, y), (width, width), 0, 0, 90, (0, 0, 0), 1)
    elif direction == 'down':
        cv2.line(img, (x, y), (x, y + height), (255, 255, 255), 3)
        cv2.ellipse(img, (x, y), (height, height), 0, 0, 90, (0, 0, 0), 1)

# 添加门
draw_door(img, 320, 350, 30, 30, 'right')  # 客厅门
draw_door(img, 350, 480, 30, 30, 'down')   # 卧室门
draw_door(img, 620, 350, 30, 30, 'right')  # 厨房门

# 绘制窗户
def draw_window(img, x, y, width, height):
    cv2.rectangle(img, (x, y), (x + width, y + height), (255, 255, 255), 3)
    cv2.rectangle(img, (x, y), (x + width, y + height), (0, 0, 0), 1)
    cv2.line(img, (x + width//2, y), (x + width//2, y + height), (0, 0, 0), 1)

# 添加窗户
draw_window(img, 200, 120, 80, 10)  # 客厅窗户
draw_window(img, 450, 120, 60, 10)  # 卧室窗户
draw_window(img, 750, 200, 10, 80)  # 厨房窗户

# 添加房间标注
cv2.putText(img, 'LIVING ROOM', (150, 220), font, 0.8, (0, 0, 0), 2)
cv2.putText(img, '6000 x 4500', (150, 250), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Area: 27.0 m²', (150, 270), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'BEDROOM 1', (400, 220), font, 0.8, (0, 0, 0), 2)
cv2.putText(img, '4200 x 3600', (400, 250), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Area: 15.1 m²', (400, 270), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'KITCHEN', (700, 220), font, 0.8, (0, 0, 0), 2)
cv2.putText(img, '3000 x 3600', (700, 250), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Area: 10.8 m²', (700, 270), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'BEDROOM 2', (150, 420), font, 0.8, (0, 0, 0), 2)
cv2.putText(img, '3600 x 3000', (150, 450), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Area: 10.8 m²', (150, 470), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'BATHROOM', (400, 420), font, 0.8, (0, 0, 0), 2)
cv2.putText(img, '2400 x 3000', (400, 450), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Area: 7.2 m²', (400, 470), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'BALCONY', (700, 420), font, 0.8, (0, 0, 0), 2)
cv2.putText(img, '2400 x 3000', (700, 450), font, 0.6, (0, 0, 0), 1)
cv2.putText(img, 'Area: 7.2 m²', (700, 470), font, 0.5, (0, 0, 0), 1)

# 添加尺寸标注
cv2.putText(img, '12000', (450, 110), font, 0.5, (0, 0, 0), 1)
cv2.putText(img, '8000', (50, 400), font, 0.5, (0, 0, 0), 1)

# 添加材料和规格说明
cv2.putText(img, 'MATERIALS & SPECIFICATIONS:', (100, 700), font, 0.6, (0, 0, 0), 2)
cv2.putText(img, '• Wall thickness: 200mm reinforced concrete', (120, 730), font, 0.4, (0, 0, 0), 1)
cv2.putText(img, '• Floor: 150mm concrete slab', (120, 750), font, 0.4, (0, 0, 0), 1)
cv2.putText(img, '• Ceiling height: 2800mm', (120, 770), font, 0.4, (0, 0, 0), 1)

# 添加总面积信息
cv2.putText(img, 'TOTAL FLOOR AREA: 70.9 m²', (600, 700), font, 0.6, (0, 0, 0), 2)
cv2.putText(img, 'BUILT-UP AREA: 85.2 m²', (600, 730), font, 0.6, (0, 0, 0), 2)

# 保存图片
cv2.imwrite('complex_building_plan.png', img)
print('✅ 创建复杂建筑图纸: complex_building_plan.png')
print('📋 包含内容:')
print('   - 6个房间标注')
print('   - 尺寸信息')
print('   - 面积计算')
print('   - 材料规格')
print('   - 门窗标识')
print('   - 图纸信息') 