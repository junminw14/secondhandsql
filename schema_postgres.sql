-- Supabase PostgreSQL 版本 schema
-- 执行前请确保在 Supabase SQL Editor 中运行

-- 清理现有数据（如果存在）
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS item CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

DROP VIEW IF EXISTS sold_items_view;
DROP VIEW IF EXISTS unsold_items_view;

-- 创建用户表（注意：user 是 PostgreSQL 保留字，需要用引号）
CREATE TABLE "user" (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE
);

-- 创建商品表
CREATE TABLE item (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC NOT NULL CHECK (price >= 0),
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    seller_id TEXT NOT NULL,
    FOREIGN KEY (seller_id) REFERENCES "user"(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 创建订单表
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL UNIQUE,
    buyer_id TEXT NOT NULL,
    order_date TEXT NOT NULL CHECK (
        order_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
    ),
    FOREIGN KEY (item_id) REFERENCES item(item_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (buyer_id) REFERENCES "user"(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 创建索引
CREATE INDEX idx_item_seller ON item(seller_id);
CREATE INDEX idx_item_status ON item(status);
CREATE INDEX idx_orders_item ON orders(item_id);
CREATE INDEX idx_orders_buyer ON orders(buyer_id);

-- 创建视图：已售商品
CREATE VIEW sold_items_view AS
SELECT
    i.item_id,
    i.item_name,
    o.buyer_id
FROM item AS i
JOIN orders AS o ON o.item_id = i.item_id
WHERE i.status = 1;

-- 创建视图：未售商品
CREATE VIEW unsold_items_view AS
SELECT
    item_id,
    item_name,
    category,
    price,
    seller_id
FROM item
WHERE status = 0;

-- 插入初始数据
INSERT INTO "user" (user_id, user_name, phone) VALUES
    ('u001', 'ZhangSan', '13800000001'),
    ('u002', 'LiSi', '13800000002'),
    ('u003', 'WangWu', '13800000003'),
    ('u004', 'ZhaoLiu', '13800000004');

INSERT INTO item (item_id, item_name, category, price, status, seller_id) VALUES
    ('i001', 'CalculusBook', 'Book', 20, 0, 'u001'),
    ('i002', 'DeskLamp', 'DailyGoods', 35, 1, 'u002'),
    ('i003', 'Microcontroller', 'Electronics', 80, 0, 'u001'),
    ('i004', 'Chair', 'Furniture', 50, 1, 'u003'),
    ('i005', 'WaterBottle', 'DailyGoods', 15, 0, 'u004');

INSERT INTO orders (order_id, item_id, buyer_id, order_date) VALUES
    ('o001', 'i002', 'u001', '2024-05-01'),
    ('o002', 'i004', 'u002', '2024-05-03');

-- 启用行级安全策略（RLS）
ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;
ALTER TABLE item ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- 创建允许所有操作的策略（因为使用 anon key 进行服务端操作）
CREATE POLICY "Allow all" ON "user" FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON item FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON orders FOR ALL USING (true) WITH CHECK (true);
