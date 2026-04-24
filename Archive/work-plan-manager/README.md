# 工作计划应用

这是一个独立的新项目，当前版本使用：

- 前端：原生 `HTML/CSS/JS`
- 后端：`Python` 标准库 HTTP 服务
- 数据库：本地 `SQLite`

数据库文件会生成在：

- [flowplan.db](/Users/ryan/Desktop/pythoncode/work-plan-manager/flowplan.db)

## 当前能力

- 计划分类、项目分组、状态筛选
- 颜色标注：红色重点、黄色关注、绿色常规
- 自定义里程碑
- 里程碑图标
- 进度、备注、成功标准、下一步动作
- 推进记录
- 时间轴视图
- SQLite 持久化存储

## 启动方式

```bash
cd /Users/ryan/Desktop/pythoncode/work-plan-manager
python3 server.py 8000
```

然后访问：

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 说明

- 不要直接双击打开 `index.html`，因为前端现在需要通过 `/api/state` 调用本地数据库接口。
- 第一次启动时会自动创建 SQLite 数据库和初始空数据。
