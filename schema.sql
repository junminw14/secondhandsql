PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS sold_items_view;
DROP VIEW IF EXISTS unsold_items_view;

DROP TRIGGER IF EXISTS orders_item_must_be_sold;
DROP TRIGGER IF EXISTS item_cannot_be_marked_unsold_with_order;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS item;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE
);

CREATE TABLE item (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    seller_id TEXT NOT NULL,
    FOREIGN KEY (seller_id) REFERENCES user(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL UNIQUE,
    buyer_id TEXT NOT NULL,
    order_date TEXT NOT NULL CHECK (
        order_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    ),
    FOREIGN KEY (item_id) REFERENCES item(item_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (buyer_id) REFERENCES user(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- Trigger: 确保订单中的商品存在且未被重复订购
CREATE TRIGGER orders_item_must_exist_and_unsold
BEFORE INSERT ON orders
FOR EACH ROW
WHEN (SELECT item_id FROM item WHERE item_id = NEW.item_id) IS NULL
  OR (SELECT COUNT(*) FROM orders WHERE item_id = NEW.item_id) > 0
BEGIN
    SELECT RAISE(ABORT, 'item does not exist or already ordered');
END;

-- Trigger: 禁止直接通过 UPDATE item 将已售商品改回未售（应通过删除订单来恢复）
CREATE TRIGGER item_cannot_be_marked_unsold_with_order
BEFORE UPDATE OF status ON item
FOR EACH ROW
WHEN NEW.status = 0
 AND OLD.status = 1
 AND EXISTS (SELECT 1 FROM orders WHERE item_id = NEW.item_id)
BEGIN
    SELECT RAISE(ABORT, 'ordered item cannot be marked unsold, delete the order first');
END;

CREATE VIEW sold_items_view AS
SELECT
    i.item_id,
    i.item_name,
    o.buyer_id
FROM item AS i
JOIN orders AS o ON o.item_id = i.item_id
WHERE i.status = 1;

CREATE INDEX idx_item_seller ON item(seller_id);
CREATE INDEX idx_item_status ON item(status);
CREATE INDEX idx_orders_item ON orders(item_id);
CREATE INDEX idx_orders_buyer ON orders(buyer_id);

CREATE VIEW unsold_items_view AS
SELECT
    item_id,
    item_name,
    category,
    price,
    seller_id
FROM item
WHERE status = 0;
