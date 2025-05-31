import cv2
import numpy as np

# 创建一个测试建筑图纸
img = np.ones((600, 800, 3), dtype=np.uint8) * 255
font = cv2.FONT_HERSHEY_SIMPLEX

# 添加标题
cv2.putText(img, 'BUILDING PLAN', (250, 50), font, 1.0, (0, 0, 0), 2)
cv2.putText(img, 'Scale: 1:100', (250, 80), font, 0.6, (0, 0, 0), 1)

# 绘制房间轮廓
cv2.rectangle(img, (100, 120), (700, 500), (0, 0, 0), 2)
cv2.line(img, (400, 120), (400, 500), (0, 0, 0), 1)
cv2.line(img, (100, 310), (700, 310), (0, 0, 0), 1)

# 添加房间标注
cv2.putText(img, 'Living Room', (150, 200), font, 0.7, (0, 0, 0), 2)
cv2.putText(img, '6000x4500', (150, 220), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'Kitchen', (450, 200), font, 0.7, (0, 0, 0), 2)
cv2.putText(img, '3000x3600', (450, 220), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'Bedroom', (150, 400), font, 0.7, (0, 0, 0), 2)
cv2.putText(img, '4200x3600', (150, 420), font, 0.5, (0, 0, 0), 1)

cv2.putText(img, 'Bathroom', (450, 400), font, 0.7, (0, 0, 0), 2)
cv2.putText(img, '2400x2100', (450, 420), font, 0.5, (0, 0, 0), 1)

# 添加说明
cv2.putText(img, 'Notes: All dimensions in mm', (100, 550), font, 0.5, (0, 0, 0), 1)

# 保存图片
cv2.imwrite('demo_building_plan.png', img)
print('✅ 创建演示建筑图纸: demo_building_plan.png') 