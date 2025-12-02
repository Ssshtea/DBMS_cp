-- ============================================
-- DATABASE IMPROVEMENTS FOR CARTIQUE APP
-- ============================================
-- This file contains triggers, stored procedures, views, and indexes
-- to make your application more dynamic and efficient
-- ============================================

USE clothing_store;

-- ============================================
-- 1. TRIGGERS
-- ============================================

-- Trigger 1: Auto-update inventory when order is placed
DELIMITER $$
CREATE TRIGGER trg_after_order_insert
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    -- Decrease product quantity (assuming quantity is 1 per order)
    UPDATE product 
    SET quantityavailable = quantityavailable - 1 
    WHERE product_id = NEW.product_id 
    AND quantityavailable > 0;
    
    -- Create inventory alert if stock is low (threshold: 10)
    IF (SELECT quantityavailable FROM product WHERE product_id = NEW.product_id) <= 10 THEN
        INSERT INTO inventory_alerts (product_id, alert_type, alert_status, created_at)
        VALUES (NEW.product_id, 'low_stock', 'pending', NOW())
        ON DUPLICATE KEY UPDATE alert_status = 'pending', created_at = NOW();
    END IF;
    
    -- Update customer lifetime value
    UPDATE customer 
    SET lifetime_value = (
        SELECT COALESCE(SUM(total_amount), 0) 
        FROM orders 
        WHERE customer_id = NEW.customer_id
    ),
    total_orders = (
        SELECT COUNT(*) 
        FROM orders 
        WHERE customer_id = NEW.customer_id
    ),
    avg_order_value = (
        SELECT COALESCE(AVG(total_amount), 0) 
        FROM orders 
        WHERE customer_id = NEW.customer_id
    )
    WHERE customer_id = NEW.customer_id;
    
    -- Log activity
    INSERT INTO activity_log (user_type, user_id, action, details, created_at)
    VALUES ('system', NEW.customer_id, 'order_placed', 
            CONCAT('Order #', NEW.order_id, ' placed'), NOW());
END$$
DELIMITER ;

-- Trigger 2: Auto-update inventory when order is cancelled/returned
DELIMITER $$
CREATE TRIGGER trg_after_order_update
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    -- If order status changed to cancelled or returned, restore inventory
    IF (OLD.status != 'Cancelled' AND NEW.status = 'Cancelled') OR
       (OLD.shipping_status != 'Returned' AND NEW.shipping_status = 'Returned') THEN
        UPDATE product 
        SET quantityavailable = quantityavailable + 1 
        WHERE product_id = NEW.product_id;
        
        -- Log activity
        INSERT INTO activity_log (user_type, user_id, action, details, created_at)
        VALUES ('system', NEW.customer_id, 'order_cancelled', 
                CONCAT('Order #', NEW.order_id, ' cancelled/returned'), NOW());
    END IF;
    
    -- If shipping status changed, log it
    IF OLD.shipping_status != NEW.shipping_status THEN
        INSERT INTO notifications (user_type, user_id, notification_type, message, created_at)
        VALUES ('customer', NEW.customer_id, 'shipping_update', 
                CONCAT('Your order #', NEW.order_id, ' status: ', NEW.shipping_status), NOW());
    END IF;
END$$
DELIMITER ;

-- Trigger 3: Auto-create notification when return is requested
DELIMITER $$
CREATE TRIGGER trg_after_return_insert
AFTER INSERT ON returns_refunds
FOR EACH ROW
BEGIN
    -- Create notification for admin
    INSERT INTO notifications (user_type, user_id, notification_type, message, created_at)
    VALUES ('admin', NULL, 'return_request', 
            CONCAT('New return request #', NEW.id, ' for order #', NEW.order_id), NOW());
    
    -- Log activity
    INSERT INTO activity_log (user_type, user_id, action, details, created_at)
    VALUES ('customer', NEW.customer_id, 'return_requested', 
            CONCAT('Return request #', NEW.id, ' created'), NOW());
END$$
DELIMITER ;

-- Trigger 4: Auto-update return status and process refund
DELIMITER $$
CREATE TRIGGER trg_after_return_update
AFTER UPDATE ON returns_refunds
FOR EACH ROW
BEGIN
    -- If return is approved, update order status
    IF OLD.status = 'Requested' AND NEW.status = 'Approved' THEN
        UPDATE orders 
        SET shipping_status = 'Returned' 
        WHERE order_id = NEW.order_id;
        
        -- Restore inventory
        UPDATE product 
        SET quantityavailable = quantityavailable + 1 
        WHERE product_id = NEW.product_id;
        
        -- Create payment record for refund
        INSERT INTO payments (order_id, customer_id, amount, payment_type, payment_status, payment_date)
        VALUES (NEW.order_id, NEW.customer_id, NEW.refund_amount, 'refund', 'completed', NOW());
        
        -- Notify customer
        INSERT INTO notifications (user_type, user_id, notification_type, message, created_at)
        VALUES ('customer', NEW.customer_id, 'return_approved', 
                CONCAT('Your return #', NEW.id, ' has been approved. Refund: ₹', NEW.refund_amount), NOW());
    END IF;
    
    -- If return is rejected, notify customer
    IF OLD.status = 'Requested' AND NEW.status = 'Rejected' THEN
        INSERT INTO notifications (user_type, user_id, notification_type, message, created_at)
        VALUES ('customer', NEW.customer_id, 'return_rejected', 
                CONCAT('Your return request #', NEW.id, ' has been rejected'), NOW());
    END IF;
END$$
DELIMITER ;

-- Trigger 5: Auto-update product stock alerts
DELIMITER $$
CREATE TRIGGER trg_after_product_update
AFTER UPDATE ON product
FOR EACH ROW
BEGIN
    -- Create or update inventory alert if stock is low
    IF NEW.quantityavailable <= 10 AND OLD.quantityavailable > 10 THEN
        INSERT INTO inventory_alerts (product_id, alert_type, alert_status, created_at)
        VALUES (NEW.product_id, 'low_stock', 'pending', NOW())
        ON DUPLICATE KEY UPDATE alert_status = 'pending', created_at = NOW();
    END IF;
    
    -- Remove alert if stock is restored
    IF NEW.quantityavailable > 10 AND OLD.quantityavailable <= 10 THEN
        UPDATE inventory_alerts 
        SET alert_status = 'resolved' 
        WHERE product_id = NEW.product_id AND alert_type = 'low_stock';
    END IF;
END$$
DELIMITER ;

-- ============================================
-- 2. STORED PROCEDURES
-- ============================================

-- Procedure 1: Process new order (with validation)
DELIMITER $$
CREATE PROCEDURE sp_process_order(
    IN p_customer_id INT,
    IN p_product_id INT,
    IN p_total_amount DECIMAL(10,2)
)
BEGIN
    DECLARE v_stock INT;
    DECLARE v_order_id INT;
    
    -- Check stock availability
    SELECT quantityavailable INTO v_stock 
    FROM product 
    WHERE product_id = p_product_id;
    
    IF v_stock <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Product out of stock';
    END IF;
    
    -- Create order
    INSERT INTO orders (customer_id, product_id, total_amount, status, shipping_status, order_date)
    VALUES (p_customer_id, p_product_id, p_total_amount, 'Pending', 'Pending', NOW());
    
    SET v_order_id = LAST_INSERT_ID();
    
    -- Return order ID
    SELECT v_order_id as order_id;
END$$
DELIMITER ;

-- Procedure 2: Get customer statistics
DELIMITER $$
CREATE PROCEDURE sp_get_customer_stats(IN p_customer_id INT)
BEGIN
    SELECT 
        c.*,
        COUNT(DISTINCT o.order_id) as total_orders,
        COALESCE(SUM(o.total_amount), 0) as total_spent,
        COALESCE(AVG(o.total_amount), 0) as avg_order_value,
        MAX(o.order_date) as last_order_date,
        CASE 
            WHEN COALESCE(SUM(o.total_amount), 0) >= 50000 THEN 'VIP'
            WHEN COALESCE(SUM(o.total_amount), 0) >= 20000 THEN 'Premium'
            WHEN COALESCE(SUM(o.total_amount), 0) >= 5000 THEN 'Regular'
            ELSE 'New'
        END as segment
    FROM customer c
    LEFT JOIN orders o ON o.customer_id = c.customer_id
    WHERE c.customer_id = p_customer_id
    GROUP BY c.customer_id;
END$$
DELIMITER ;

-- Procedure 3: Get dashboard statistics
DELIMITER $$
CREATE PROCEDURE sp_get_dashboard_stats()
BEGIN
    SELECT 
        (SELECT COUNT(*) FROM product) as total_products,
        (SELECT COUNT(*) FROM orders) as total_orders,
        (SELECT COALESCE(SUM(total_amount), 0) FROM orders) as total_revenue,
        (SELECT COUNT(*) FROM orders WHERE DATE(order_date) = CURDATE()) as orders_today,
        (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE DATE(order_date) = CURDATE()) as revenue_today,
        (SELECT COUNT(*) FROM orders WHERE status = 'Pending') as pending_orders,
        (SELECT COUNT(*) FROM product WHERE quantityavailable <= 10) as low_stock_count,
        (SELECT COUNT(*) FROM returns_refunds WHERE status = 'Requested') as pending_returns;
END$$
DELIMITER ;

-- Procedure 4: Update customer segment based on spending
DELIMITER $$
CREATE PROCEDURE sp_update_customer_segments()
BEGIN
    UPDATE customer c
    SET segment = (
        SELECT CASE 
            WHEN COALESCE(SUM(o.total_amount), 0) >= 50000 THEN 'VIP'
            WHEN COALESCE(SUM(o.total_amount), 0) >= 20000 THEN 'Premium'
            WHEN COALESCE(SUM(o.total_amount), 0) >= 5000 THEN 'Regular'
            ELSE 'New'
        END
        FROM orders o
        WHERE o.customer_id = c.customer_id
    );
END$$
DELIMITER ;

-- ============================================
-- 3. VIEWS (for common queries)
-- ============================================

-- View 1: Order details with customer and product info
CREATE OR REPLACE VIEW v_order_details AS
SELECT 
    o.order_id,
    o.order_date,
    o.total_amount,
    o.status,
    o.shipping_status,
    o.tracking_number,
    c.customer_id,
    c.name as customer_name,
    c.email as customer_email,
    c.phone as customer_phone,
    p.product_id,
    p.name as product_name,
    p.category as product_category,
    p.price as product_price
FROM orders o
LEFT JOIN customer c ON c.customer_id = o.customer_id
LEFT JOIN product p ON p.product_id = o.product_id;

-- View 2: Product sales summary
CREATE OR REPLACE VIEW v_product_sales AS
SELECT 
    p.product_id,
    p.name,
    p.category,
    p.price,
    p.quantityavailable,
    COUNT(o.order_id) as total_orders,
    COALESCE(SUM(o.total_amount), 0) as total_revenue,
    COALESCE(AVG(o.total_amount), 0) as avg_order_value
FROM product p
LEFT JOIN orders o ON o.product_id = p.product_id
GROUP BY p.product_id, p.name, p.category, p.price, p.quantityavailable;

-- View 3: Customer summary with orders
CREATE OR REPLACE VIEW v_customer_summary AS
SELECT 
    c.customer_id,
    c.name,
    c.email,
    c.phone,
    c.blocked,
    COUNT(DISTINCT o.order_id) as total_orders,
    COALESCE(SUM(o.total_amount), 0) as lifetime_value,
    COALESCE(AVG(o.total_amount), 0) as avg_order_value,
    MAX(o.order_date) as last_order_date,
    CASE 
        WHEN COALESCE(SUM(o.total_amount), 0) >= 50000 THEN 'VIP'
        WHEN COALESCE(SUM(o.total_amount), 0) >= 20000 THEN 'Premium'
        WHEN COALESCE(SUM(o.total_amount), 0) >= 5000 THEN 'Regular'
        ELSE 'New'
    END as segment
FROM customer c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name, c.email, c.phone, c.blocked;

-- View 4: Daily sales summary
CREATE OR REPLACE VIEW v_daily_sales AS
SELECT 
    DATE(order_date) as sale_date,
    COUNT(*) as order_count,
    COALESCE(SUM(total_amount), 0) as total_revenue,
    COALESCE(AVG(total_amount), 0) as avg_order_value
FROM orders
GROUP BY DATE(order_date);

-- ============================================
-- 4. INDEXES (for performance optimization)
-- ============================================

-- Indexes on orders table
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_product_id ON orders(product_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_shipping_status ON orders(shipping_status);
CREATE INDEX idx_orders_date_status ON orders(order_date, status);

-- Indexes on product table
CREATE INDEX idx_product_category ON product(category);
CREATE INDEX idx_product_seller ON product(seller_id);
CREATE INDEX idx_product_stock ON product(quantityavailable);

-- Indexes on customer table
CREATE INDEX idx_customer_email ON customer(email);
CREATE INDEX idx_customer_blocked ON customer(blocked);

-- Indexes on returns_refunds table
CREATE INDEX idx_returns_order_id ON returns_refunds(order_id);
CREATE INDEX idx_returns_status ON returns_refunds(status);
CREATE INDEX idx_returns_customer_id ON returns_refunds(customer_id);

-- Indexes on notifications table
CREATE INDEX idx_notifications_user ON notifications(user_type, user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);

-- Indexes on activity_log table
CREATE INDEX idx_activity_user ON activity_log(user_type, user_id);
CREATE INDEX idx_activity_created ON activity_log(created_at);

-- ============================================
-- 5. ADDITIONAL COLUMNS (if needed)
-- ============================================

-- Add updated_at timestamp to orders (if not exists)
-- ALTER TABLE orders ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Add segment column to customer (if not exists)
-- ALTER TABLE customer ADD COLUMN segment VARCHAR(20) DEFAULT 'New';

-- Add total_orders and avg_order_value to customer (if not exists)
-- ALTER TABLE customer ADD COLUMN total_orders INT DEFAULT 0;
-- ALTER TABLE customer ADD COLUMN avg_order_value DECIMAL(10,2) DEFAULT 0.00;

-- ============================================
-- 6. USEFUL QUERIES TO RUN PERIODICALLY
-- ============================================

-- Update all customer segments (run daily via cron or scheduled event)
-- CALL sp_update_customer_segments();

-- Clean old notifications (older than 30 days)
-- DELETE FROM notifications WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) AND is_read = TRUE;

-- Clean old activity logs (older than 90 days)
-- DELETE FROM activity_log WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Update analytics cache (if you add caching)
-- This would be handled by your application, but you could create a procedure for it

-- ============================================
-- 7. EVENT SCHEDULER (for automated tasks)
-- ============================================

-- Enable event scheduler
SET GLOBAL event_scheduler = ON;

-- Event 1: Update customer segments daily
CREATE EVENT evt_update_customer_segments
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_DATE + INTERVAL 1 DAY
DO
  CALL sp_update_customer_segments();

-- Event 2: Clean old notifications weekly
CREATE EVENT evt_clean_old_notifications
ON SCHEDULE EVERY 1 WEEK
STARTS CURRENT_DATE + INTERVAL 1 WEEK
DO
  DELETE FROM notifications 
  WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY) 
  AND is_read = TRUE;

-- Event 3: Clean old activity logs monthly
CREATE EVENT evt_clean_old_activity_logs
ON SCHEDULE EVERY 1 MONTH
STARTS DATE_FORMAT(NOW() + INTERVAL 1 MONTH, '%Y-%m-01')
DO
  DELETE FROM activity_log 
  WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- ============================================
-- END OF DATABASE IMPROVEMENTS
-- ============================================

