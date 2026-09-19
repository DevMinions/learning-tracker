# Learning Tracker

管理学习计划、追踪进度、记录打卡的技能。

## 功能

- **创建学习计划** - 设定目标、时间、每日学习时间
- **记录打卡** - 记录每天学了什么、学了多久
- **查看进度** - 显示总学习时间、连续打卡天数、任务完成情况
- **生成报告** - 自动生成学习进度报告

## 安装

```bash
# 克隆到本地
git clone https://github.com/your-username/learning-tracker.git

# 复制到技能目录
cp -r learning-tracker ~/.agents/skills/
```

## 使用方式

### 创建学习计划

```
帮我制定一个学习算法工程师的计划，3个月，每天2小时
```

### 记录打卡

```
我今天看了3Blue1Brown线性代数视频，学了45分钟
```

### 查看进度

```
查看我的学习进度
```

## 数据存储

所有数据存储在项目目录的 `.learning/` 文件夹：

```
.learning/
├── plan.json           # 学习计划
├── progress.json       # 进度数据
├── checkins/           # 打卡记录
│   └── YYYY-MM-DD.json
└── reports/            # 生成的报告
```

## 技能结构

```
learning-tracker/
├── SKILL.md            # 技能说明
├── scripts/
│   └── tracker.py      # 数据管理脚本
├── evals/
│   └── evals.json      # 测试用例
└── README.md           # 本文档
```

## 示例

### 创建计划

```python
from tracker import LearningTracker

tracker = LearningTracker()
tracker.init_plan("成为算法工程师", "2026-09-19", "2026-12-31", 2)
tracker.add_task("线性代数基础", 10)
tracker.add_task("Python编程", 15)
```

### 打卡记录

```python
tracker.checkin("task-1", "看了矩阵乘法视频", 45, completed=True)
```

### 查看进度

```python
print(tracker.generate_report())
```

## 许可证

MIT License
