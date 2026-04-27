INSERT INTO user (user_id, user_name, phone) VALUES
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
