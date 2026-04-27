# 校园二手交易平台数据库系统

## 使用说明

最终提交时，推荐直接使用打包目录中的启动脚本：

1. 打开 [dist/secondhandsql](<D:/Code/Project/secondhandsql/dist/secondhandsql>)
2. 双击 [run.bat](<D:/Code/Project/secondhandsql/dist/secondhandsql/run.bat>)
3. 如果弹出管理员确认，点击“是”
4. 程序会自动：
   - 清理已知的阻止规则
   - 添加允许访问的防火墙规则
   - 启动网站
   - 自动打开浏览器
5. 电脑端访问 `http://127.0.0.1:5000`
6. 手机端使用首页二维码扫码，或输入控制台显示的局域网地址访问

如果只是本机演示，也可以直接访问 `http://127.0.0.1:5000`。

## 目录

- [一、推荐运行方式](#一推荐运行方式)
- [二、如果手机端打不开](#二如果手机端打不开)
- [三、源码运行方式](#三源码运行方式)
- [四、项目结构](#四项目结构)
- [五、页面与功能](#五页面与功能)
- [六、数据库实现说明](#六数据库实现说明)
- [七、安全性与并发恢复简答](#七安全性与并发恢复简答)

## 一、推荐运行方式

### 1. 打包版运行

这是给老师和同学使用的方式，不需要额外安装 Python：

1. 进入 [dist/secondhandsql](<D:/Code/Project/secondhandsql/dist/secondhandsql>)
2. 双击 [run.bat](<D:/Code/Project/secondhandsql/dist/secondhandsql/run.bat>)
3. 若弹出管理员确认，点击“是”
4. 浏览器会自动打开首页

启动成功后可通过以下地址访问：

- 本机地址：`http://127.0.0.1:5000`
- 局域网地址：`http://本机局域网IP:5000`

说明：

- 打包版目录中已经带有运行环境
- 首次运行时会在打包目录生成 `secondhandsql.db`
- 首页和控制台都会显示手机访问方式

### 2. 为什么建议同意管理员权限

为了尽量做到“新手一遍过”，启动器会自动处理最常见的 Windows 防火墙阻断：

- 删除针对 `secondhandsql.exe` 的入站阻止规则
- 添加程序级允许规则
- 添加 `5000` 端口允许规则

这一步属于目标电脑自己的系统权限配置，所以首次运行时可能需要管理员确认一次。

## 二、如果手机端打不开

### 1. 先确认访问方式

优先按下面顺序测试：

1. 电脑本机访问 `http://127.0.0.1:5000`
2. 手机访问控制台打印的局域网地址
3. 手机扫码首页二维码

如果第 1 步能打开，而手机打不开，通常是局域网访问或防火墙问题，不是网站本身没启动。

### 2. 先重新走一次推荐启动流程

请先关闭程序，再重新双击 [dist/secondhandsql/run.bat](<D:/Code/Project/secondhandsql/dist/secondhandsql/run.bat>)，并确保：

- 弹出管理员确认时点击“是”
- 不要直接跳过启动器去手动运行其他命令

### 3. 如果仍失败，手动配置防火墙

以管理员身份打开 PowerShell，执行：

```powershell
Get-NetFirewallRule -DisplayName "secondhandsql" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "SecondHandSQL App" -Direction Inbound -Program "你的secondhandsql.exe完整路径" -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "SecondHandSQL Port 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Any
```

如果是当前项目默认打包路径，`exe` 路径通常是：

`D:\Code\Project\secondhandsql\dist\secondhandsql\secondhandsql.exe`

### 4. 手动界面配置方法

如果不想用命令行，也可以手动操作：

1. 打开“Windows 安全中心”
2. 进入“防火墙和网络保护”
3. 检查是否存在阻止 `secondhandsql.exe` 的规则
4. 允许该程序通过防火墙
5. 确保 TCP `5000` 端口没有被拦截

### 5. 关于手机热点

当前项目已经尽量把“打包”和“常见防火墙放行”自动化了。  
但如果使用手机热点做局域网，仍可能遇到少数机型或热点实现差异。

更稳的测试方式：

1. 电脑连接 A 手机热点
2. B 手机也连接 A 手机热点
3. 用 B 手机访问电脑地址

如果 B 手机能访问，而热点提供方那台手机自己不能访问，这通常是热点实现差异，不是项目代码错误。

## 三、源码运行方式

源码运行适合开发和调试，不是最终交付的主要入口。

执行：

```bash
pip install -r requirements.txt
python app.py
```

然后访问：

- `http://127.0.0.1:5000`

## 四、项目结构

- [app.py](<D:/Code/Project/secondhandsql/app.py>)：Flask 主程序
- [schema.sql](<D:/Code/Project/secondhandsql/schema.sql>)：建表、约束、触发器、视图
- [init_data.sql](<D:/Code/Project/secondhandsql/init_data.sql>)：初始数据
- [templates](<D:/Code/Project/secondhandsql/templates>)：HTML 模板
- [static/style.css](<D:/Code/Project/secondhandsql/static/style.css>)：页面样式
- [launcher.ps1](<D:/Code/Project/secondhandsql/launcher.ps1>)：启动时自动处理防火墙规则
- [run.bat](<D:/Code/Project/secondhandsql/run.bat>)：统一入口脚本
- [build_portable.bat](<D:/Code/Project/secondhandsql/build_portable.bat>)：重新打包脚本
- [dist/secondhandsql](<D:/Code/Project/secondhandsql/dist/secondhandsql>)：最终免安装交付目录

## 五、页面与功能

### 首页

- 展示系统简介
- 展示本机和局域网访问地址
- 展示二维码
- 展示统计信息
- 支持重置数据库

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

- 基本查询 4 项
- 连接查询 3 项
- 聚合与分组 4 项
- 视图 2 项

## 六、数据库实现说明

### 1. 表结构

- `user(user_id, user_name, phone)`
- `item(item_id, item_name, category, price, status, seller_id)`
- `orders(order_id, item_id, buyer_id, order_date)`

### 2. 约束

- 三张表均设置主键
- 外键关系完整
- `item.status` 只允许 `0` 或 `1`
- `orders.item_id` 唯一，保证每个商品最多交易一次

### 3. 视图

- `sold_items_view`
- `unsold_items_view`

### 4. 业务逻辑

购买商品使用事务：

1. 检查商品是否存在且未售出
2. 更新商品状态为已售出
3. 插入订单记录
4. 任一步失败则回滚

## 七、安全性与并发恢复简答

### 1. 如何防止普通用户删除数据

在真实数据库环境中，应只给管理员分配删除权限，并在应用层隐藏高权限入口。

### 2. 如何限制用户只能查询数据

可以创建只读账号，只授予 `SELECT` 权限；应用层只提供查询接口。

### 3. 两个用户同时购买同一商品会出现什么问题

可能发生重复购买或状态不一致。

### 4. 如何解决

使用事务、状态检查和唯一约束。

### 5. 如果系统崩溃，如何恢复订单数据

通过数据库备份、WAL 文件或定期导出 SQL 恢复。
