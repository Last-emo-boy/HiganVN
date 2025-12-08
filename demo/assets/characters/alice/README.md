# 差分立绘素材放置指南

## 文件夹结构

```
alice/
├── manifest.json           # 角色配置文件
├── base/                   # 身体底图
│   ├── normal.png          # 普通站姿 (1024x1536)
│   └── cross_arms.png      # 抱臂姿势
├── face/                   # 表情
│   ├── normal.png          # 整合表情：普通
│   ├── happy.png           # 整合表情：开心
│   ├── sad.png             # 整合表情：难过
│   ├── angry.png           # 整合表情：生气
│   ├── surprise.png        # 整合表情：惊讶
│   ├── shy.png             # 整合表情：害羞
│   └── parts/              # 分离式表情部件（可选）
│       ├── eyes_normal.png
│       ├── eyes_closed.png
│       ├── mouth_smile.png
│       ├── brows_normal.png
│       └── brows_angry.png
├── outfit/                 # 服装
│   ├── school/             # 制服
│   │   ├── body.png        # 服装主体
│   │   └── ribbon.png      # 领带/配饰
│   └── casual/             # 便服
│       └── body.png
└── effects/                # 特效层
    ├── blush.png           # 脸红
    └── sweat.png           # 汗滴
```

## 素材规格

- **画布尺寸**: 1024x1536 像素
- **格式**: PNG（带透明通道）
- **表情位置**: 需要与 face_offset 配合

## 合成顺序 (Z-Order)

1. **BASE (0)**: 身体底图
2. **OUTFIT (50)**: 服装
3. **ACCESSORY (55)**: 配饰
4. **FACE_COMPOSITE (100)**: 整合表情
5. **MOUTH (101)**: 嘴巴
6. **EYES (102)**: 眼睛
7. **EYEBROWS (103)**: 眉毛
8. **EFFECT (150+)**: 特效

## 使用方式

脚本中调用：
```
# 显示角色（姿势:表情:服装）
爱丽丝 (normal:happy:school) "你好！"

# 切换表情
爱丽丝 (happy) "开心~"

# 添加特效
爱丽丝 (shy+blush) "好害羞..."

# 自定义组合
爱丽丝 (custom_smile:school) "自定义表情"
```
