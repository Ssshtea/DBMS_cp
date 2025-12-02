# DBMS Concepts Documentation - Cartique Application

## Table of Contents
1. [Database Configuration](#database-configuration)
2. [Connection Management](#connection-management)
3. [Core Database Functions](#core-database-functions)
4. [Database Tables](#database-tables)
5. [Database Views](#database-views)
6. [Stored Procedures](#stored-procedures)
7. [API Endpoints & Database Operations](#api-endpoints--database-operations)
8. [DBMS Concepts Used](#dbms-concepts-used)

---

## Database Configuration

### Connection Pool Configuration
**Location:** Lines 11-23

**DBMS Concept:** Connection Pooling

**Configuration Details:**
- **Host:** localhost
- **Database:** clothing_store
- **Pool Size:** 10 connections
- **Pool Name:** mypool
- **Charset:** utf8mb4
- **Collation:** utf8mb4_unicode_ci
- **Autocommit:** False (explicit transaction control)

**Purpose:** Manages a pool of database connections to improve performance and resource management.

---

## Connection Management

### 1. `init_pool()`
**Location:** Lines 28-36

**DBMS Concept:** Connection Pool Initialization

**Functionality:**
- Initializes MySQL connection pool using `mysql.connector.pooling.MySQLConnectionPool`
- Creates a pool of 10 reusable database connections
- Handles initialization errors

**Database Connection:** Establishes connection pool to `clothing_store` database

---

### 2. `get_db_connection()`
**Location:** Lines 38-55

**DBMS Concept:** Connection Retrieval with Retry Logic

**Functionality:**
- Retrieves a connection from the pool
- Implements retry logic (3 attempts with exponential backoff)
- Handles connection failures gracefully

**Database Connection:** Gets connection from pool to `clothing_store` database

---

### 3. `execute_query(query, params=None, fetch=False)`
**Location:** Lines 57-136

**DBMS Concepts:** 
- Query Execution
- Transaction Management (COMMIT/ROLLBACK)
- Cursor Management
- Error Handling

**Functionality:**
- Executes SQL queries with parameterized inputs (prevents SQL injection)
- Manages transactions explicitly (COMMIT for INSERT/UPDATE/DELETE)
- Handles ROLLBACK on errors
- Supports both fetch (SELECT) and non-fetch (INSERT/UPDATE/DELETE) operations
- Implements retry logic for failed queries

**Transaction Control:**
- **Autocommit:** Disabled (explicit commits)
- **Commit:** Line 79 - Explicit commit after INSERT/UPDATE/DELETE
- **Rollback:** Lines 89, 117 - Rollback on errors

**Database Connection:** Uses connection from pool to execute queries

---

## Database Tables

### 1. `admin` Table
**Used in:** Multiple endpoints

**Columns Referenced:**
- `admin_id` (Primary Key)
- `username`
- `password`
- `email`

**Operations:**
- SELECT (authentication, user listing)
- INSERT (create admin user)
- UPDATE (update admin user)
- DELETE (delete admin user)

**Related Endpoints:**
- `/api/admin/login` - SELECT with WHERE clause
- `/api/admin/users` - SELECT, INSERT, UPDATE, DELETE

---

### 2. `product` Table
**Used in:** Product management endpoints

**Columns Referenced:**
- `product_id` (Primary Key)
- `name`
- `description`
- `price`
- `category`
- `quantityavailable`
- `seller_id` (Foreign Key to `seller` table)

**Operations:**
- SELECT (list, search, filter)
- INSERT (add product)
- UPDATE (update product)
- DELETE (delete product)

**Related Endpoints:**
- `/api/admin/products` - Full CRUD operations
- `/api/admin/products/<id>/analytics` - SELECT with JOINs
- `/api/admin/inventory/low-stock` - SELECT with WHERE and ORDER BY

**DBMS Concepts:**
- Foreign Key relationship with `seller` table
- Aggregation (COUNT, SUM, AVG)
- GROUP BY (category statistics)
- WHERE clauses (filtering)

---

### 3. `orders` Table
**Used in:** Order management endpoints

**Columns Referenced:**
- `order_id` (Primary Key)
- `customer_id` (Foreign Key to `customer` table)
- `product_id` (Foreign Key to `product` table)
- `order_date`
- `total_amount`
- `status`
- `shipping_status`
- `tracking_number`
- `last_updated`

**Operations:**
- SELECT (list, filter, aggregate)
- UPDATE (status, shipping status, tracking)
- DELETE (not directly used, but referenced)

**Related Endpoints:**
- `/api/admin/orders` - SELECT with JOINs
- `/api/admin/orders/<id>` - UPDATE
- `/api/admin/dashboard` - Aggregation queries

**DBMS Concepts:**
- Foreign Keys (customer_id, product_id)
- Date functions (DATE_FORMAT, CURDATE, DATE_SUB)
- Aggregation (COUNT, SUM, AVG)
- GROUP BY (monthly sales, status grouping)
- JOINs (with customer, product tables)
- CASE statements (conditional aggregation)

---

### 4. `customer` Table
**Used in:** Customer management endpoints

**Columns Referenced:**
- `customer_id` (Primary Key)
- `name`
- `email`
- `phone`
- `blocked`
- `lifetime_value` (calculated field)
- `segment` (calculated field)
- `total_orders` (calculated field)
- `avg_order_value` (calculated field)

**Operations:**
- SELECT (list, filter, aggregate)
- UPDATE (toggle blocked status, update segments)

**Related Endpoints:**
- `/api/admin/customers` - SELECT
- `/api/admin/customers/<id>/toggle` - UPDATE
- `/api/admin/customers/top` - SELECT with ORDER BY and LIMIT

**DBMS Concepts:**
- Calculated fields (lifetime_value, segment)
- Aggregation (AVG, SUM, COUNT)
- GROUP BY (segmentation)
- ORDER BY (sorting)

---

### 5. `seller` Table
**Used in:** Seller management endpoints

**Columns Referenced:**
- `id` (Primary Key)
- `name`
- `company`
- `email`
- `phone`

**Operations:**
- SELECT (list sellers)
- INSERT (add seller)
- UPDATE (update seller)
- DELETE (delete seller)

**Related Endpoints:**
- `/api/admin/sellers` - Full CRUD operations

**DBMS Concepts:**
- Foreign Key relationship (referenced by `product.seller_id`)

---

### 6. `reviews` Table
**Used in:** Review management endpoints

**Columns Referenced:**
- `review_id` (Primary Key)
- `product_id` (Foreign Key)
- `customer_id` (Foreign Key)
- `rating`
- `comment`
- `status` (approved, pending, rejected)
- `created_at`

**Operations:**
- SELECT (list, filter by product, status)
- UPDATE (update status)
- DELETE (delete review)

**Related Endpoints:**
- `/api/admin/reviews` - SELECT with JOINs and WHERE
- `/api/admin/reviews/<id>` - UPDATE, DELETE

**DBMS Concepts:**
- Foreign Keys (product_id, customer_id)
- JOINs (with product and customer tables)
- WHERE clauses (filtering by product_id, status)
- Date formatting (DATE_FORMAT)

---

### 7. `returns_refunds` Table
**Used in:** Returns and refunds management

**Columns Referenced:**
- `id` (Primary Key)
- `order_id` (Foreign Key)
- `product_id` (Foreign Key)
- `customer_id` (Foreign Key)
- `reason`
- `status` (Requested, Approved, Rejected, Refunded)
- `refund_amount`
- `created_at`

**Operations:**
- SELECT (list, filter by status)
- INSERT (create return request)
- UPDATE (update status)

**Related Endpoints:**
- `/api/admin/returns` - SELECT with JOINs
- `/api/admin/returns` (POST) - INSERT
- `/api/admin/returns/<id>` - UPDATE

**DBMS Concepts:**
- Foreign Keys (order_id, product_id, customer_id)
- JOINs (with orders, customer, product tables)
- WHERE clauses (status filtering)
- Aggregation (COUNT for pending returns)

---

### 8. `notifications` Table
**Used in:** Notification system

**Columns Referenced:**
- `notification_id` (Primary Key)
- `user_type`
- `message`
- `is_read`
- `created_at`

**Operations:**
- SELECT (list notifications)
- UPDATE (mark as read)

**Related Endpoints:**
- `/api/admin/notifications` - SELECT with WHERE and ORDER BY
- `/api/admin/notifications/<id>/read` - UPDATE

**DBMS Concepts:**
- WHERE clauses (user_type filtering)
- ORDER BY (sorting by created_at)
- LIMIT (pagination)

---

### 9. `activity_log` Table
**Used in:** Activity tracking

**Columns Referenced:**
- All columns (SELECT *)
- `user_type`
- `created_at`

**Operations:**
- SELECT (list activities)

**Related Endpoints:**
- `/api/admin/activity` - SELECT with WHERE, ORDER BY, LIMIT
- `/api/admin/audit-logs` - SELECT with pagination (LIMIT/OFFSET)

**DBMS Concepts:**
- WHERE clauses (user_type filtering)
- ORDER BY (sorting by created_at)
- LIMIT and OFFSET (pagination)
- Aggregation (COUNT for total)

---

### 10. `inventory_alerts` Table
**Used in:** Inventory management

**Columns Referenced:**
- All columns
- `product_id` (Foreign Key)
- `alert_status`

**Operations:**
- SELECT (list alerts)

**Related Endpoints:**
- `/api/admin/inventory-alerts` - SELECT with JOIN

**DBMS Concepts:**
- Foreign Key (product_id)
- JOIN (with product table)
- WHERE clauses (alert_status filtering)

---

### 11. `coupons` Table
**Used in:** Discount management

**Columns Referenced:**
- `coupon_id` (Primary Key)
- `code` (UNIQUE)
- `discount_type`
- `discount_value`
- `min_purchase`
- `max_discount`
- `valid_from`
- `valid_until`
- `usage_limit`
- `used_count`
- `status`
- `created_at`

**Operations:**
- SELECT (list coupons)
- INSERT (create coupon)
- UPDATE (update coupon)

**Related Endpoints:**
- `/api/admin/coupons` - SELECT, INSERT, UPDATE

**DBMS Concepts:**
- UNIQUE constraint (code)
- Date fields (valid_from, valid_until)
- Table creation (CREATE TABLE IF NOT EXISTS)

---

### 12. `settings` Table
**Used in:** System settings

**Columns Referenced:**
- `id` (Primary Key)
- `key` (UNIQUE)
- `value`

**Operations:**
- SELECT (get settings)
- INSERT (create setting)
- UPDATE (update setting using ON DUPLICATE KEY UPDATE)

**Related Endpoints:**
- `/api/admin/settings` - SELECT, UPDATE

**DBMS Concepts:**
- UNIQUE constraint (key)
- INSERT ... ON DUPLICATE KEY UPDATE (upsert operation)

---

## Database Views

### 1. `v_order_details` View
**Used in:** Multiple order-related endpoints

**Purpose:** Optimized view combining order, customer, and product data

**Referenced in:**
- `/api/admin/orders` (Line 545)
- `/api/admin/customers/<id>/history` (Line 1669)
- `/api/admin/orders/recent` (Line 1944)
- `/api/admin/bills/<id>/pdf` (Line 2074)

**DBMS Concept:** Database View (pre-computed JOIN for performance)

**Benefits:**
- Reduces query complexity
- Improves performance by pre-joining tables
- Provides consistent data structure

---

### 2. `v_customer_summary` View
**Used in:** Customer analytics and segmentation

**Purpose:** Pre-calculated customer statistics

**Referenced in:**
- `/api/admin/customers` (Line 606)
- `/api/admin/customers/top` (Line 1649)
- `/api/admin/customers/segments` (Line 850)

**DBMS Concept:** Database View with Aggregated Data

**Contains:**
- Customer details
- Lifetime value (pre-calculated)
- Total orders (pre-calculated)
- Average order value (pre-calculated)
- Segment classification

---

### 3. `v_product_sales` View
**Used in:** Product analytics

**Purpose:** Pre-calculated product sales statistics

**Referenced in:**
- `/api/admin/products/<id>/analytics` (Line 827)
- `/api/admin/analytics/category-performance` (Line 1924)

**DBMS Concept:** Database View with Aggregated Sales Data

**Contains:**
- Product details
- Total orders (pre-calculated)
- Total revenue (pre-calculated)
- Sales metrics

---

### 4. `v_daily_sales` View
**Used in:** Daily sales reporting

**Purpose:** Pre-calculated daily sales data

**Referenced in:**
- `/api/admin/reports/daily-sales` (Line 1898)

**DBMS Concept:** Database View with Date-based Aggregation

**Benefits:**
- Pre-aggregated daily sales
- Faster reporting queries

---

## Stored Procedures

### 1. `sp_update_customer_segments()`
**Location:** Line 865

**Purpose:** Updates customer segmentation based on purchase behavior

**DBMS Concept:** Stored Procedure

**Called in:**
- `/api/admin/customers/update-segments` (POST)

**Functionality:**
- Calculates customer segments (New, Regular, VIP, etc.)
- Updates customer table with segment information

---

### 2. `sp_get_customer_stats(customer_id)`
**Location:** Line 1697

**Purpose:** Retrieves comprehensive statistics for a specific customer

**DBMS Concept:** Stored Procedure with Parameters

**Called in:**
- `/api/admin/customers/<id>/stats`

**Functionality:**
- Returns aggregated customer statistics
- Calculates lifetime value, order count, average order value

---

## API Endpoints & Database Operations

### Authentication & Admin Management

#### `/api/admin/login` (POST)
**Function:** `api_login()`
**Location:** Lines 172-191

**Database Operations:**
- **Query Type:** SELECT
- **Table:** `admin`
- **Columns:** `admin_id`, `username`, `password`
- **WHERE Clause:** `username=%s AND password=%s`
- **DBMS Concept:** Authentication query with parameterized inputs

**SQL Equivalent:**
```sql
SELECT * FROM admin WHERE username=? AND password=?
```

---

#### `/api/admin/users` (GET, POST, PUT, DELETE)
**Functions:** `api_get_admin_users()`, `api_create_admin_user()`, `api_update_admin_user()`, `api_delete_admin_user()`
**Location:** Lines 1308-1386

**Database Operations:**
- **GET:** SELECT from `admin` table
- **POST:** INSERT into `admin` table with validation (check existing username)
- **PUT:** UPDATE `admin` table (dynamic updates)
- **DELETE:** DELETE from `admin` table

**DBMS Concepts:**
- Parameterized queries
- Transaction management
- Data validation (checking for existing records)

---

### Dashboard & Statistics

#### `/api/admin/dashboard` (GET)
**Function:** `api_dashboard()`
**Location:** Lines 194-238

**Database Operations:**
1. **Total Products:**
   - **Query:** `SELECT COUNT(*) as total_products FROM product`
   - **DBMS Concept:** Aggregation (COUNT)

2. **Total Orders:**
   - **Query:** `SELECT COUNT(*) as total_orders FROM orders`
   - **DBMS Concept:** Aggregation (COUNT)

3. **Total Revenue:**
   - **Query:** `SELECT COALESCE(SUM(total_amount), 0) as total_revenue FROM orders`
   - **DBMS Concept:** Aggregation (SUM), COALESCE for NULL handling

4. **Orders Today:**
   - **Query:** `SELECT COUNT(*) FROM orders WHERE DATE(order_date) = CURDATE()`
   - **DBMS Concept:** Date functions (DATE, CURDATE), WHERE clause

5. **Revenue Today:**
   - **Query:** `SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE DATE(order_date) = CURDATE()`
   - **DBMS Concept:** Aggregation with date filtering

6. **Pending Orders:**
   - **Query:** `SELECT COUNT(*) FROM orders WHERE status = 'Pending'`
   - **DBMS Concept:** Conditional aggregation

7. **Low Stock Count:**
   - **Query:** `SELECT COUNT(*) FROM product WHERE quantityavailable <= 10`
   - **DBMS Concept:** Conditional WHERE clause

8. **Pending Returns:**
   - **Query:** `SELECT COUNT(*) FROM returns_refunds WHERE status = 'Requested'`
   - **DBMS Concept:** Conditional aggregation

---

#### `/api/admin/dashboard/monthly-sales` (GET)
**Function:** `monthly_sales()`
**Location:** Lines 241-253

**Database Operations:**
- **Query:** 
  ```sql
  SELECT DATE_FORMAT(order_date, '%Y-%m') as month, SUM(total_amount) as total
  FROM orders
  GROUP BY month
  ORDER BY month
  ```
- **Tables:** `orders`
- **DBMS Concepts:**
  - Date formatting (DATE_FORMAT)
  - Aggregation (SUM)
  - GROUP BY
  - ORDER BY

---

#### `/api/admin/dashboard/revenue-summary` (GET)
**Function:** `api_revenue_summary()`
**Location:** Lines 256-297

**Database Operations:**
- **Query:** Complex aggregation with CASE statements
- **Tables:** `orders`
- **DBMS Concepts:**
  - Conditional aggregation (CASE WHEN)
  - Date functions (CURDATE, DATE_SUB, MONTH, YEAR)
  - COALESCE for NULL handling
  - Single query for multiple time periods

**SQL Structure:**
```sql
SELECT 
    COALESCE(SUM(CASE WHEN DATE(order_date) = CURDATE() THEN total_amount ELSE 0 END), 0) as today,
    COALESCE(SUM(CASE WHEN order_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN total_amount ELSE 0 END), 0) as week,
    COALESCE(SUM(CASE WHEN MONTH(order_date) = MONTH(CURDATE()) AND YEAR(order_date) = YEAR(CURDATE()) THEN total_amount ELSE 0 END), 0) as month,
    COALESCE(SUM(total_amount), 0) as total
FROM orders
```

---

#### `/api/admin/dashboard/best-sellers` (GET)
**Function:** `best_sellers()`
**Location:** Lines 300-314

**Database Operations:**
- **Query:** 
  ```sql
  SELECT p.name, COUNT(*) as total_qty
  FROM orders o
  JOIN product p ON p.product_id = o.product_id
  GROUP BY p.name, p.product_id
  ORDER BY total_qty DESC
  LIMIT 10
  ```
- **Tables:** `orders`, `product`
- **DBMS Concepts:**
  - INNER JOIN
  - Aggregation (COUNT)
  - GROUP BY
  - ORDER BY (DESC)
  - LIMIT

---

### Product Management

#### `/api/admin/products` (GET, POST, PUT, DELETE)
**Functions:** `api_products()`, `api_add_product()`, `api_update_product()`, `api_delete_product()`
**Location:** Lines 317-457

**Database Operations:**

1. **GET - List Products:**
   - **Query:** `SELECT * FROM product`
   - **Table:** `product`
   - **DBMS Concept:** Simple SELECT

2. **POST - Add Product:**
   - **Query:** 
     ```sql
     INSERT INTO product (name, description, price, category, quantityavailable, seller_id)
     VALUES (%s, %s, %s, %s, %s, %s)
     ```
   - **Table:** `product`
   - **DBMS Concepts:**
     - INSERT with multiple columns
     - Foreign key (seller_id)
     - Transaction management (explicit COMMIT)
     - `lastrowid` to get inserted ID

3. **PUT - Update Product:**
   - **Query:**
     ```sql
     UPDATE product SET name=%s, description=%s, price=%s, category=%s, quantityavailable=%s, seller_id=%s
     WHERE product_id=%s
     ```
   - **Table:** `product`
   - **DBMS Concepts:**
     - UPDATE with WHERE clause
     - Transaction management
     - Data validation (check if product exists)

4. **DELETE - Delete Product:**
   - **Query:** `DELETE FROM product WHERE product_id=%s`
   - **Table:** `product`
   - **DBMS Concept:** DELETE with WHERE clause

---

#### `/api/admin/products/<id>/analytics` (GET)
**Function:** `api_product_analytics()`
**Location:** Lines 820-835

**Database Operations:**
- **Query:** `SELECT * FROM v_product_sales WHERE product_id = %s`
- **View:** `v_product_sales`
- **DBMS Concept:** View usage for optimized queries

---

#### `/api/admin/products/search` (GET)
**Function:** `api_search_products()`
**Location:** Lines 1956-1996

**Database Operations:**
- **Query:** Dynamic SELECT with multiple WHERE conditions
- **Table:** `product`
- **DBMS Concepts:**
  - Dynamic query building
  - LIKE operator for pattern matching
  - Multiple WHERE conditions (AND)
  - Parameterized queries

**Query Structure:**
```sql
SELECT * FROM product 
WHERE 1=1
  AND (name LIKE %s OR description LIKE %s)  -- Search term
  AND category = %s                            -- Category filter
  AND price >= %s                             -- Min price
  AND price <= %s                             -- Max price
  AND quantityavailable > 0                   -- Stock filter
ORDER BY product_id DESC
```

---

### Order Management

#### `/api/admin/orders` (GET)
**Function:** `api_orders()`
**Location:** Lines 538-567

**Database Operations:**
- **Query:** 
  ```sql
  SELECT *, DATE_FORMAT(order_date, '%Y-%m-%d') as date
  FROM v_order_details
  ORDER BY order_date DESC
  ```
- **View:** `v_order_details`
- **DBMS Concepts:**
  - View usage
  - Date formatting
  - ORDER BY

---

#### `/api/admin/orders/<id>` (PUT)
**Function:** `api_update_order_status()`
**Location:** Lines 569-598

**Database Operations:**
- **Query:** Dynamic UPDATE query
- **Table:** `orders`
- **DBMS Concepts:**
  - Dynamic UPDATE (building SET clause)
  - WHERE clause
  - NOW() function for timestamp
  - Multiple column updates

**Query Structure:**
```sql
UPDATE orders 
SET status = %s, shipping_status = %s, tracking_number = %s, last_updated = NOW()
WHERE order_id = %s
```

---

#### `/api/admin/orders/bulk-update` (PUT)
**Function:** `api_bulk_update_orders()`
**Location:** Lines 887-903

**Database Operations:**
- **Query:** 
  ```sql
  UPDATE orders 
  SET status = %s, last_updated = NOW()
  WHERE order_id IN (%s, %s, ...)
  ```
- **Table:** `orders`
- **DBMS Concepts:**
  - Bulk UPDATE
  - IN clause for multiple values
  - Dynamic placeholder generation

---

### Customer Management

#### `/api/admin/customers` (GET)
**Function:** `api_customers()`
**Location:** Lines 601-612

**Database Operations:**
- **Query:** `SELECT * FROM v_customer_summary ORDER BY lifetime_value DESC`
- **View:** `v_customer_summary`
- **DBMS Concepts:**
  - View usage
  - ORDER BY (DESC)

---

#### `/api/admin/customers/<id>/toggle` (PUT)
**Function:** `api_toggle_customer()`
**Location:** Lines 614-622

**Database Operations:**
1. **SELECT:** `SELECT blocked FROM customer WHERE customer_id=%s`
2. **UPDATE:** `UPDATE customer SET blocked=%s WHERE customer_id=%s`
- **Table:** `customer`
- **DBMS Concepts:**
  - SELECT before UPDATE (read current value)
  - Conditional UPDATE (toggle boolean)

---

#### `/api/admin/customers/segments` (GET)
**Function:** `api_customer_segments()`
**Location:** Lines 838-859

**Database Operations:**
- **Query:**
  ```sql
  SELECT 
      COALESCE(segment, 'New') as segment, 
      COUNT(*) as count, 
      COALESCE(AVG(lifetime_value), 0) as avg_value,
      COALESCE(SUM(lifetime_value), 0) as total_value,
      COALESCE(AVG(total_orders), 0) as avg_orders
  FROM v_customer_summary 
  GROUP BY segment
  ORDER BY avg_value DESC
  ```
- **View:** `v_customer_summary`
- **DBMS Concepts:**
  - Aggregation (COUNT, AVG, SUM)
  - GROUP BY
  - COALESCE for NULL handling
  - ORDER BY

---

### Reports & Analytics

#### `/api/admin/reports/sales-by-category` (GET)
**Function:** `api_sales_by_category_report()`
**Location:** Lines 625-671

**Database Operations:**
- **Query:** Complex aggregation with date filtering
- **Tables:** `orders`, `product`
- **DBMS Concepts:**
  - JOIN (INNER JOIN)
  - Aggregation (COUNT, SUM, AVG)
  - GROUP BY
  - WHERE clause with date range
  - Dynamic query building
  - Date handling (month format conversion)

**Query Structure:**
```sql
SELECT 
    p.category,
    COUNT(DISTINCT o.order_id) as order_count,
    COUNT(*) as total_qty,
    SUM(o.total_amount) as revenue,
    AVG(o.total_amount) as avg_price
FROM orders o
JOIN product p ON p.product_id = o.product_id
WHERE 1=1
  AND o.order_date >= %s  -- Optional from_date
  AND o.order_date <= %s  -- Optional to_date
GROUP BY p.category
ORDER BY revenue DESC
```

---

#### `/api/admin/reports/revenue` (GET)
**Function:** `api_revenue_report()`
**Location:** Lines 674-721

**Database Operations:**
1. **Total Revenue:**
   ```sql
   SELECT COALESCE(SUM(total_amount), 0) as total_revenue 
   FROM orders 
   WHERE order_date >= %s AND order_date <= %s
   ```

2. **Monthly Breakdown:**
   ```sql
   SELECT DATE_FORMAT(order_date, '%Y-%m') as month, 
          COALESCE(SUM(total_amount), 0) as total,
          COUNT(*) as order_count
   FROM orders 
   WHERE order_date >= %s AND order_date <= %s
   GROUP BY month
   ORDER BY month
   ```
- **Table:** `orders`
- **DBMS Concepts:**
  - Date range filtering
  - Date formatting
  - Aggregation (SUM, COUNT)
  - GROUP BY
  - ORDER BY

---

### Database Management Features

#### `/api/admin/db/tables` (GET)
**Function:** `api_get_tables()`
**Location:** Lines 1079-1088

**Database Operations:**
- **Query:** `SHOW TABLES`
- **DBMS Concept:** Metadata query (information schema access)

---

#### `/api/admin/db/table/<table_name>/structure` (GET)
**Function:** `api_get_table_structure()`
**Location:** Lines 1090-1098

**Database Operations:**
- **Query:** `DESCRIBE <table_name>`
- **DBMS Concept:** Metadata query (table structure)

---

#### `/api/admin/db/table/<table_name>/data` (GET)
**Function:** `api_get_table_data()`
**Location:** Lines 1100-1125

**Database Operations:**
1. **Count Query:** `SELECT COUNT(*) as total FROM <table_name>`
2. **Data Query:** `SELECT * FROM <table_name> LIMIT %s OFFSET %s`
- **DBMS Concepts:**
  - Pagination (LIMIT/OFFSET)
  - Aggregation (COUNT)

---

#### `/api/admin/db/query` (POST)
**Function:** `api_execute_custom_query()`
**Location:** Lines 1128-1149

**Database Operations:**
- **Query:** User-provided SELECT query
- **DBMS Concepts:**
  - Dynamic query execution
  - Security restrictions (only SELECT allowed)
  - Query validation

**Security Features:**
- Only SELECT queries allowed
- Blocks dangerous keywords (DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE)

---

#### `/api/admin/db/statistics` (GET)
**Function:** `api_database_statistics()`
**Location:** Lines 1152-1194

**Database Operations:**
1. **Table Sizes:**
   ```sql
   SELECT 
       table_name AS 'table',
       ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'size_mb',
       table_rows AS 'rows'
   FROM information_schema.TABLES 
   WHERE table_schema = DATABASE()
   ORDER BY (data_length + index_length) DESC
   ```

2. **Database Size:**
   ```sql
   SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'db_size_mb'
   FROM information_schema.TABLES 
   WHERE table_schema = DATABASE()
   ```

3. **Row Counts:** `SELECT COUNT(*) FROM <each_table>`
- **DBMS Concepts:**
  - Information schema access
  - Metadata queries
  - Aggregation (SUM, COUNT)
  - Mathematical operations (ROUND)

---

#### `/api/admin/db/health` (GET)
**Function:** `api_database_health()`
**Location:** Lines 1197-1238

**Database Operations:**
1. **Test Query:** `SELECT 1 as test`
2. **Max Connections:** `SHOW VARIABLES LIKE 'max_connections'`
3. **Active Connections:** `SHOW STATUS LIKE 'Threads_connected'`
- **DBMS Concepts:**
  - Health check queries
  - System variables access
  - Performance monitoring

---

#### `/api/admin/db/optimize` (POST)
**Function:** `api_optimize_database()`
**Location:** Lines 1579-1604

**Database Operations:**
- **Query:** `OPTIMIZE TABLE <table_name>`
- **DBMS Concept:** Table optimization (maintenance operation)

---

### Data Validation

#### `/api/admin/validate/data` (GET)
**Function:** `api_validate_data()`
**Location:** Lines 1520-1576

**Database Operations:**
1. **Orphaned Products:**
   ```sql
   SELECT p.product_id, p.name 
   FROM product p 
   LEFT JOIN seller s ON s.id = p.seller_id 
   WHERE p.seller_id IS NOT NULL AND s.id IS NULL
   ```

2. **Orphaned Orders:**
   ```sql
   SELECT o.order_id 
   FROM orders o 
   LEFT JOIN customer c ON c.customer_id = o.customer_id 
   WHERE o.customer_id IS NOT NULL AND c.customer_id IS NULL
   ```

3. **Negative Stock:**
   ```sql
   SELECT product_id, name, quantityavailable 
   FROM product 
   WHERE quantityavailable < 0
   ```
- **DBMS Concepts:**
  - LEFT JOIN for referential integrity checking
  - NULL checking (IS NULL, IS NOT NULL)
  - Data validation queries

---

### Import/Export

#### `/api/admin/export/all` (GET)
**Function:** `api_export_all_data()`
**Location:** Lines 1241-1259

**Database Operations:**
- **Query:** `SELECT * FROM <each_table>`
- **DBMS Concept:** Full table export

---

#### `/api/admin/import/csv` (POST)
**Function:** `api_import_csv()`
**Location:** Lines 1272-1305

**Database Operations:**
- **Query:** 
  ```sql
  INSERT INTO <table_name> (<columns>) VALUES (<values>)
  ```
- **DBMS Concepts:**
  - Bulk INSERT
  - Dynamic column mapping
  - Transaction management

---

### Advanced Features

#### `/api/admin/analytics/sales-forecast` (GET)
**Function:** `api_sales_forecast()`
**Location:** Lines 967-982

**Database Operations:**
- **Query:**
  ```sql
  SELECT DATE_FORMAT(order_date, '%Y-%m') as month, 
         SUM(total_amount) as revenue,
         COUNT(*) as orders
  FROM orders 
  WHERE order_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
  GROUP BY month
  ORDER BY month
  ```
- **Table:** `orders`
- **DBMS Concepts:**
  - Date functions (DATE_FORMAT, DATE_SUB, NOW)
  - Aggregation (SUM, COUNT)
  - GROUP BY
  - Time-based filtering

---

#### `/api/admin/analytics/category-performance` (GET)
**Function:** `api_category_performance()`
**Location:** Lines 1910-1933

**Database Operations:**
- **Query:** Complex aggregation using view
- **View:** `v_product_sales`
- **DBMS Concepts:**
  - View usage
  - Aggregation (COUNT, SUM, AVG)
  - GROUP BY
  - CASE statements
  - COALESCE

---

## DBMS Concepts Used

### 1. Connection Management
- **Connection Pooling:** Reusable connection pool (10 connections)
- **Connection Retry Logic:** Exponential backoff retry mechanism
- **Connection Lifecycle:** Proper connection acquisition and release

### 2. Transaction Management
- **Autocommit:** Disabled (explicit control)
- **COMMIT:** Explicit commits after INSERT/UPDATE/DELETE
- **ROLLBACK:** Automatic rollback on errors
- **Transaction Isolation:** Default MySQL isolation level

### 3. SQL Operations

#### Data Manipulation Language (DML)
- **SELECT:** Querying data with various clauses
- **INSERT:** Adding new records
- **UPDATE:** Modifying existing records
- **DELETE:** Removing records

#### Data Definition Language (DDL)
- **CREATE TABLE:** Table creation (coupons, settings)
- **DESCRIBE:** Table structure inspection
- **SHOW TABLES:** List all tables
- **OPTIMIZE TABLE:** Table maintenance

### 4. Query Clauses

#### WHERE Clause
- Equality conditions (`column = value`)
- Comparison operators (`<=`, `>=`, `<`, `>`)
- NULL checking (`IS NULL`, `IS NOT NULL`)
- Pattern matching (`LIKE` with `%`)
- Multiple conditions (`AND`, `OR`)
- IN clause for multiple values

#### JOIN Operations
- **INNER JOIN:** Matching records from multiple tables
- **LEFT JOIN:** All records from left table, matching from right
- **JOIN ON:** Explicit join conditions

#### Aggregation Functions
- **COUNT:** Count rows
- **SUM:** Sum numeric values
- **AVG:** Average calculation
- **MAX/MIN:** Maximum/minimum values
- **DISTINCT:** Unique value counting

#### GROUP BY
- Grouping rows by column values
- Used with aggregation functions
- Multiple column grouping

#### ORDER BY
- Sorting results (ASC/DESC)
- Multiple column sorting

#### LIMIT/OFFSET
- Pagination support
- Result set limiting

### 5. Advanced SQL Features

#### Date Functions
- **DATE_FORMAT:** Format date values
- **CURDATE:** Current date
- **NOW:** Current timestamp
- **DATE:** Extract date part
- **DATE_SUB:** Subtract time intervals
- **MONTH/YEAR:** Extract date components

#### Conditional Logic
- **CASE WHEN:** Conditional expressions
- **COALESCE:** NULL value handling
- **IF/ELSE logic:** In stored procedures

#### String Operations
- **LIKE:** Pattern matching
- **CONCAT:** String concatenation (implied)

### 6. Database Objects

#### Tables
- Primary keys (auto-increment)
- Foreign keys (referential integrity)
- Unique constraints
- Default values
- Data types (INT, VARCHAR, DECIMAL, TIMESTAMP, DATE, TEXT)

#### Views
- Pre-computed JOINs
- Aggregated data views
- Performance optimization
- Data abstraction

#### Stored Procedures
- Parameterized procedures
- Business logic encapsulation
- Reusable code

#### Triggers (Referenced)
- Auto-calculation of fields (lifetime_value)
- Data consistency maintenance

### 7. Security Features

#### SQL Injection Prevention
- Parameterized queries (all queries use `%s` placeholders)
- Input validation
- Query sanitization

#### Access Control
- Read-only query restrictions
- Dangerous keyword blocking
- User authentication

### 8. Performance Optimization

#### Indexing (Implied)
- Primary key indexes
- Foreign key indexes
- Query optimization

#### View Usage
- Pre-computed aggregations
- Reduced JOIN complexity
- Faster query execution

#### Query Optimization
- Efficient JOIN strategies
- Proper WHERE clause usage
- LIMIT for large result sets

### 9. Data Integrity

#### Referential Integrity
- Foreign key relationships
- Orphaned record detection
- Data validation queries

#### Constraints
- Primary key constraints
- Unique constraints
- Foreign key constraints
- NOT NULL constraints (implied)

### 10. Metadata Queries

#### Information Schema
- Table information
- Database statistics
- Connection information
- Table sizes and row counts

### 11. Error Handling

#### Transaction Rollback
- Automatic rollback on errors
- Error logging
- Retry mechanisms

#### Exception Handling
- Try-catch blocks
- Error propagation
- Graceful degradation

---

## Summary

This application demonstrates comprehensive use of MySQL database management concepts:

1. **Connection Management:** Connection pooling, retry logic, proper resource management
2. **Transaction Control:** Explicit commits, rollbacks, transaction isolation
3. **CRUD Operations:** Complete Create, Read, Update, Delete operations
4. **Advanced Queries:** JOINs, aggregations, subqueries, complex WHERE clauses
5. **Database Objects:** Tables, Views, Stored Procedures
6. **Performance:** Views for optimization, pagination, efficient queries
7. **Security:** Parameterized queries, input validation, access control
8. **Data Integrity:** Foreign keys, validation queries, referential integrity
9. **Metadata Access:** Information schema queries, table inspection
10. **Date/Time Operations:** Extensive use of date functions for reporting

The application uses **MySQL** as the DBMS with the **mysql.connector** Python library, implementing best practices for database connectivity, security, and performance optimization.

