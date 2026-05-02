# 校园二手交易平台数据库系统

## 使用说明

项目已经部署到 Vercel，可直接通过公网地址访问。打包版仍保留给本机演示或离线演示使用。

### 打包版运行

1. 打开 [dist/secondhandsql](<D:/Code/Project/secondhandsql/dist/secondhandsql>)
2. 双击 [run.bat](<D:/Code/Project/secondhandsql/dist/secondhandsql/run.bat>)
3. 浏览器会自动打开 `http://127.0.0.1:5000`

说明：

- 首次运行会在打包目录生成 `secondhandsql.db`
- 本地运行只监听 `127.0.0.1:5000`
- 不再申请管理员权限，也不再配置 Windows 防火墙规则

### 源码运行

```bash
pip install -r requirements.txt
python app.py
```

然后访问：

- `http://127.0.0.1:5000`

## 项目结构

- [app.py](<D:/Code/Project/secondhandsql/app.py>)：Flask 主程序
- [schema.sql](<D:/Code/Project/secondhandsql/schema.sql>)：建表、约束、触发器、视图
- [init_data.sql](<D:/Code/Project/secondhandsql/init_data.sql>)：初始数据
- [templates](<D:/Code/Project/secondhandsql/templates>)：HTML 模板
- [static/style.css](<D:/Code/Project/secondhandsql/static/style.css>)：页面样式
- [launcher.ps1](<D:/Code/Project/secondhandsql/launcher.ps1>)：本机打包版启动器
- [run.bat](<D:/Code/Project/secondhandsql/run.bat>)：统一入口脚本
- [build_portable.bat](<D:/Code/Project/secondhandsql/build_portable.bat>)：重新打包脚本

## 页面与功能

### 首页

- 展示系统简介
- 展示统计信息
- 管理员登录后可重置数据库

### 用户列表页

- 展示 `user` 表全部数据

### 商品列表页

- 新增商品
- 修改价格
- 删除未售商品
- 购买商品

### 订单列表页

- 展示 `orders` 表及订单明细

### 查询结果页

- 基本查询
- 连接查询
- 聚合与分组
- 视图查询

## 数据库实现说明

- `user(user_id, user_name, phone)`
- `item(item_id, item_name, category, price, status, seller_id)`
- `orders(order_id, item_id, buyer_id, order_date)`

约束：

- 三张表均设置主键
- 外键关系完整
- `item.status` 只允许 `0` 或 `1`
- `orders.item_id` 唯一，保证每个商品最多交易一次

购买商品使用事务：

1. 检查商品是否存在且未售出
2. 更新商品状态为已售出
3. 插入订单记录
4. 任一步失败则回滚
