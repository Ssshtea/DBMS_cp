from flask import Flask, render_template, request, jsonify, send_file
import mysql.connector
from mysql.connector import Error, pooling
import time
from datetime import datetime, timedelta
from io import BytesIO

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'clothing_store',
    'autocommit': False,  # We'll commit explicitly like the working code
    'connect_timeout': 10,
    'pool_name': 'mypool',
    'pool_size': 10,
    'pool_reset_session': True,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# Connection pool
pool = None

def init_pool():
    """Initialize connection pool"""
    global pool
    try:
        pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
        print("✅ Connection pool initialized")
    except Error as e:
        print(f"❌ Failed to initialize connection pool: {e}")
        raise

def get_db_connection():
    """Get database connection from pool with retry logic"""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            if pool is None:
                init_pool()
            conn = pool.get_connection()
            return conn
        except Error as e:
            print(f"❌ Database connection failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise e

def execute_query(query, params=None, fetch=False):
    """Execute database query with automatic reconnection - using explicit commits like working code"""
    conn = None
    cursor = None
    
    for attempt in range(3):
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True, buffered=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                result = cursor.fetchall()
                cursor.close()
                conn.close()
                return result
            else:
                # For INSERT/UPDATE/DELETE - EXPLICIT COMMIT like working code
                conn.commit()  # This is critical - explicit commit like db.py
                cursor.close()
                conn.close()
                return True
                
        except Error as e:
            print(f"❌ Query failed (attempt {attempt + 1}): {e}")
            print(f"   Query: {query[:100]}...")  # Print first 100 chars of query for debugging
            if conn:
                try:
                    conn.rollback()  # Rollback on error
                except:
                    pass
            if cursor:
                try:
                    # Only try to fetch if it's a SELECT query and we haven't fetched yet
                    if fetch and query.strip().upper().startswith('SELECT'):
                        try:
                            cursor.fetchall()
                        except:
                            pass
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass
            if attempt < 2:
                time.sleep(1)
            else:
                raise e
        except Exception as e:
            print(f"❌ Unexpected error (attempt {attempt + 1}): {e}")
            print(f"   Query: {query[:100]}...")  # Print first 100 chars of query for debugging
            if conn:
                try:
                    conn.rollback()  # Rollback on error
                except:
                    pass
            if cursor:
                try:
                    # Only try to fetch if it's a SELECT query and we haven't fetched yet
                    if fetch and query.strip().upper().startswith('SELECT'):
                        try:
                            cursor.fetchall()
                        except:
                            pass
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass
            raise e

# Initialize connection pool
try:
    init_pool()
    print("✅ Database connection pool ready")
    # Test connection using execute_query to ensure proper handling
    test_result = execute_query("SELECT 1 as test", fetch=True)
    print("✅ Database connection test successful")
except Error as e:
    print(f"❌ Failed to establish database connection pool: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Unexpected error during database initialization: {e}")
    import traceback
    traceback.print_exc()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/test-db')
def test_db():
    """Test endpoint to verify database connection"""
    try:
        result = execute_query("SELECT 1 as test", fetch=True)
        return jsonify({'success': True, 'message': 'Database connection working', 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- Serve Admin Panel ----------
@app.route('/admin')
def admin_panel():
    return render_template('index.html')

@app.route('/api/admin/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        admin = execute_query(
            "SELECT * FROM admin WHERE username=%s AND password=%s", 
            (username, password), 
            fetch=True
        )

        if admin:
            return jsonify({'success': True, 'admin_id': admin[0]['admin_id'], 'username': admin[0]['username']})
        else:
            return jsonify({'success': False})
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Dashboard Stats ----------
@app.route('/api/admin/dashboard')
def api_dashboard():
    """Get dashboard stats - using direct queries for accuracy"""
    try:
        # Use direct queries instead of stored procedure for better compatibility
        total_products = execute_query("SELECT COUNT(*) as total_products FROM product", fetch=True)[0]['total_products']
        total_orders = execute_query("SELECT COUNT(*) as total_orders FROM orders", fetch=True)[0]['total_orders']
        total_revenue = execute_query("SELECT COALESCE(SUM(total_amount), 0) as total_revenue FROM orders", fetch=True)[0]['total_revenue'] or 0
        
        # Additional stats
        orders_today = execute_query("SELECT COUNT(*) as orders_today FROM orders WHERE DATE(order_date) = CURDATE()", fetch=True)[0]['orders_today']
        revenue_today = execute_query("SELECT COALESCE(SUM(total_amount), 0) as revenue_today FROM orders WHERE DATE(order_date) = CURDATE()", fetch=True)[0]['revenue_today'] or 0
        pending_orders = execute_query("SELECT COUNT(*) as pending_orders FROM orders WHERE status = 'Pending'", fetch=True)[0]['pending_orders']
        low_stock_count = execute_query("SELECT COUNT(*) as low_stock_count FROM product WHERE quantityavailable <= 10", fetch=True)[0]['low_stock_count']
        
        # Check if returns_refunds table exists
        try:
            pending_returns = execute_query("SELECT COUNT(*) as pending_returns FROM returns_refunds WHERE status = 'Requested'", fetch=True)[0]['pending_returns']
        except:
            pending_returns = 0

        return jsonify({
            'total_products': int(total_products),
            'total_orders': int(total_orders),
            'total_revenue': float(total_revenue),
            'orders_today': int(orders_today),
            'revenue_today': float(revenue_today),
            'pending_orders': int(pending_orders),
            'low_stock_count': int(low_stock_count),
            'pending_returns': int(pending_returns)
        })
    except Exception as e:
        print(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'total_products': 0,
            'total_orders': 0,
            'total_revenue': 0,
            'orders_today': 0,
            'revenue_today': 0,
            'pending_orders': 0,
            'low_stock_count': 0,
            'pending_returns': 0
        })

# Monthly Sales (last 12 months)
@app.route('/api/admin/dashboard/monthly-sales')
def monthly_sales():
    try:
        result = execute_query("""
            SELECT DATE_FORMAT(order_date, '%Y-%m') as month, SUM(total_amount) as total
            FROM orders
            GROUP BY month
            ORDER BY month
        """, fetch=True)
        return jsonify(result)
    except Exception as e:
        print(f"Monthly sales error: {e}")
        return jsonify([])

# Revenue Summary
@app.route('/api/admin/dashboard/revenue-summary')
def api_revenue_summary():
    """Get revenue summary for dashboard"""
    try:
        # Get all revenue data in one query for better performance
        result = execute_query("""
            SELECT 
                COALESCE(SUM(CASE WHEN DATE(order_date) = CURDATE() THEN total_amount ELSE 0 END), 0) as today,
                COALESCE(SUM(CASE WHEN order_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN total_amount ELSE 0 END), 0) as week,
                COALESCE(SUM(CASE WHEN MONTH(order_date) = MONTH(CURDATE()) AND YEAR(order_date) = YEAR(CURDATE()) THEN total_amount ELSE 0 END), 0) as month,
                COALESCE(SUM(total_amount), 0) as total
            FROM orders
        """, fetch=True)
        
        if result and len(result) > 0:
            data = result[0]
            return jsonify({
                'success': True,
                'today': float(data.get('today', 0) or 0),
                'week': float(data.get('week', 0) or 0),
                'month': float(data.get('month', 0) or 0),
                'total': float(data.get('total', 0) or 0)
            })
        else:
            return jsonify({
                'success': True,
                'today': 0.0,
                'week': 0.0,
                'month': 0.0,
                'total': 0.0
            })
    except Exception as e:
        print(f"Revenue summary error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'today': 0.0,
            'week': 0.0,
            'month': 0.0,
            'total': 0.0
        })

# Best Sellers
@app.route('/api/admin/dashboard/best-sellers')
def best_sellers():
    try:
        result = execute_query("""
            SELECT p.name, COUNT(*) as total_qty
            FROM orders o
            JOIN product p ON p.product_id = o.product_id
            GROUP BY p.name, p.product_id
            ORDER BY total_qty DESC
            LIMIT 10
        """, fetch=True)
        return jsonify(result)
    except Exception as e:
        print(f"Best sellers error: {e}")
        return jsonify([])

# ---------- Products CRUD ----------
@app.route('/api/admin/products', methods=['GET'])
def api_products():
    try:
        products = execute_query("SELECT * FROM product", fetch=True)
        return jsonify(products)
    except Exception as e:
        print(f"Products fetch error: {e}")
        return jsonify([])

@app.route('/api/admin/products', methods=['POST'])
def api_add_product():
    try:
        data = request.json
        print(f"📦 Adding product: {data}")  # Debug log
        
        # Validate required fields
        if not data.get('name') or not data.get('price') or not data.get('category'):
            return jsonify({'success': False, 'error': 'Missing required fields: name, price, or category'})
        
        # Get connection and cursor for this operation
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        try:
            # Execute INSERT
            cursor.execute(
                "INSERT INTO product (name, description, price, category, quantityavailable, seller_id) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    data['name'],
                    data.get('description', ''),
                    float(data['price']),
                    data['category'],
                    int(data.get('quantityavailable', 0)),
                    int(data.get('seller_id')) if data.get('seller_id') else None
                )
            )
            
            # Get the inserted product_id
            product_id = cursor.lastrowid
            
            # Commit the transaction
            conn.commit()
            
            print(f"✅ Product inserted successfully with ID: {product_id}")
            
            # Fetch the complete product to return
            cursor.execute("SELECT * FROM product WHERE product_id = %s", (product_id,))
            new_product = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'product_id': product_id, 'product': new_product})
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Add product error: {error_msg}")
        print(f"   Data received: {data}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/admin/products/<int:id>', methods=['PUT'])
def api_update_product(id):
    try:
        data = request.json
        print(f"📝 Updating product {id}: {data}")  # Debug log
        
        # Validate required fields
        if not data.get('name') or not data.get('price') or not data.get('category'):
            return jsonify({'success': False, 'error': 'Missing required fields: name, price, or category'})
        
        # Get connection and cursor for this operation
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        try:
            # Check if product exists
            cursor.execute("SELECT product_id FROM product WHERE product_id = %s", (id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Product not found'})
            
            # Execute UPDATE
            cursor.execute(
                "UPDATE product SET name=%s, description=%s, price=%s, category=%s, quantityavailable=%s, seller_id=%s WHERE product_id=%s",
                (
                    data['name'],
                    data.get('description', ''),
                    float(data['price']),
                    data['category'],
                    int(data.get('quantityavailable', 0)),
                    int(data.get('seller_id')) if data.get('seller_id') else None,
                    id
                )
            )
            
            # Commit the transaction
            conn.commit()
            
            print(f"✅ Product updated successfully")
            
            # Fetch the updated product to return
            cursor.execute("SELECT * FROM product WHERE product_id = %s", (id,))
            updated_product = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'product': updated_product})
            
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            raise e
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Update product error: {error_msg}")
        print(f"   Data received: {data}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/admin/products/<int:id>', methods=['DELETE'])
def api_delete_product(id):
    try:
        execute_query("DELETE FROM product WHERE product_id=%s", (id,))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete product error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Sellers CRUD ----------
@app.route('/api/admin/sellers', methods=['GET'])
def api_sellers():
    try:
        sellers = execute_query("SELECT * FROM seller", fetch=True)
        return jsonify(sellers)
    except Exception as e:
        print(f"Sellers fetch error: {e}")
        return jsonify([])

@app.route('/api/admin/sellers', methods=['POST'])
def api_add_seller():
    try:
        data = request.json
        print(f"👤 Adding seller: {data}")  # Debug log
        
        # Validate required fields
        if not data.get('name') or not data.get('email'):
            return jsonify({'success': False, 'error': 'Missing required fields: name or email'})
        
        result = execute_query(
            "INSERT INTO seller (name, company, email, phone) VALUES (%s,%s,%s,%s)",
            (
                data['name'],
                data.get('company', ''),
                data['email'],
                data.get('phone', '')
            )
        )
        print(f"✅ Seller added successfully: {result}")
        return jsonify({'success': True})
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Add seller error: {error_msg}")
        print(f"   Data received: {data}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/admin/sellers/<int:id>', methods=['PUT'])
def api_update_seller(id):
    try:
        data = request.json
        print(f"📝 Updating seller {id}: {data}")  # Debug log
        
        # Validate required fields
        if not data.get('name') or not data.get('email'):
            return jsonify({'success': False, 'error': 'Missing required fields: name or email'})
        
        result = execute_query(
            "UPDATE seller SET name=%s, company=%s, email=%s, phone=%s WHERE id=%s",
            (
                data['name'],
                data.get('company', ''),
                data['email'],
                data.get('phone', ''),
                id
            )
        )
        print(f"✅ Seller updated successfully: {result}")
        return jsonify({'success': True})
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Update seller error: {error_msg}")
        print(f"   Data received: {data}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': error_msg})

@app.route('/api/admin/sellers/<int:id>', methods=['DELETE'])
def api_delete_seller(id):
    try:
        execute_query("DELETE FROM seller WHERE id=%s", (id,))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete seller error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Orders ----------
@app.route('/api/admin/orders', methods=['GET'])
def api_orders():
    """Get orders using optimized view"""
    try:
        # Use the v_order_details view for better performance
        orders = execute_query("""
            SELECT *, DATE_FORMAT(order_date, '%Y-%m-%d') as date
            FROM v_order_details
            ORDER BY order_date DESC
        """, fetch=True)
        
        result = []
        for o in orders:
            # Create items array from order data
            if o.get('product_id') and o.get('product_name'):
                o['items'] = [{
                    'name': o.get('product_name', 'N/A'),
                    'category': o.get('product_category', 'N/A'),
                    'qty': 1,  # Default quantity since it's not in orders table
                    'price': float(o.get('product_price', o.get('total_amount', 0)))
                }]
            else:
                o['items'] = []
            result.append(o)
        return jsonify(result)
    except Exception as e:
        print(f"Orders fetch error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/admin/orders/<int:id>', methods=['PUT'])
def api_update_order_status(id):
    try:
        data = request.json
        # Update status and/or shipping_status
        updates = []
        params = []
        
        if 'status' in data:
            updates.append("status = %s")
            params.append(data['status'])
        
        if 'shipping_status' in data:
            updates.append("shipping_status = %s")
            params.append(data['shipping_status'])
        
        if 'tracking_number' in data:
            updates.append("tracking_number = %s")
            params.append(data.get('tracking_number'))
        
        if not updates:
            return jsonify({'success': False, 'error': 'No fields to update'})
        
        params.append(id)
        query = f"UPDATE orders SET {', '.join(updates)}, last_updated = NOW() WHERE order_id = %s"
        execute_query(query, tuple(params))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update order status error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Customers ----------
@app.route('/api/admin/customers', methods=['GET'])
def api_customers():
    """Get customers using optimized view with pre-calculated stats"""
    try:
        # Use v_customer_summary view which includes all calculated fields
        customers = execute_query("SELECT * FROM v_customer_summary ORDER BY lifetime_value DESC", fetch=True)
        return jsonify(customers)
    except Exception as e:
        print(f"Customers fetch error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/admin/customers/<int:id>/toggle', methods=['PUT'])
def api_toggle_customer(id):
    try:
        blocked = execute_query("SELECT blocked FROM customer WHERE customer_id=%s", (id,), fetch=True)[0]['blocked']
        execute_query("UPDATE customer SET blocked=%s WHERE customer_id=%s", (0 if blocked else 1, id))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Toggle customer error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Reports: Sales by Category with Date Range ----------
@app.route('/api/admin/reports/sales-by-category')
def api_sales_by_category_report():
    """Get sales by category for a date range"""
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        
        # Build query with optional date filter
        query = """
            SELECT 
                p.category,
                COUNT(DISTINCT o.order_id) as order_count,
                COUNT(*) as total_qty,
                SUM(o.total_amount) as revenue,
                AVG(o.total_amount) as avg_price
            FROM orders o
            JOIN product p ON p.product_id = o.product_id
            WHERE 1=1
        """
        params = []
        
        if from_date:
            if len(from_date) == 7:
                from_date = f"{from_date}-01"
            query += " AND o.order_date >= %s"
            params.append(from_date)
        
        if to_date:
            if len(to_date) == 7:
                year, month = map(int, to_date.split('-'))
                if month == 12:
                    last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = datetime(year, month + 1, 1) - timedelta(days=1)
                to_date = last_day.strftime('%Y-%m-%d')
            query += " AND o.order_date <= %s"
            params.append(to_date)
        
        query += " GROUP BY p.category ORDER BY revenue DESC"
        
        result = execute_query(query, tuple(params) if params else None, fetch=True)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"Sales by category report error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ---------- Reports ----------
@app.route('/api/admin/reports/revenue')
def api_revenue_report():
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    try:
        # Convert month format (YYYY-MM) to date range
        if from_date and len(from_date) == 7:  # Format: YYYY-MM
            from_date = f"{from_date}-01"
        if to_date and len(to_date) == 7:  # Format: YYYY-MM
            # Get last day of the month
            year, month = map(int, to_date.split('-'))
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)
            to_date = last_day.strftime('%Y-%m-%d')
        
        # Get total revenue for the period
        total_revenue = execute_query("""
            SELECT COALESCE(SUM(total_amount), 0) as total_revenue 
            FROM orders 
            WHERE order_date >= %s AND order_date <= %s
        """, (from_date, to_date), fetch=True)[0]['total_revenue'] or 0
        
        # Get monthly breakdown
        monthly_data = execute_query("""
            SELECT DATE_FORMAT(order_date, '%Y-%m') as month, 
                   COALESCE(SUM(total_amount), 0) as total,
                   COUNT(*) as order_count
            FROM orders 
            WHERE order_date >= %s AND order_date <= %s
            GROUP BY month
            ORDER BY month
        """, (from_date, to_date), fetch=True)
        
        return jsonify({
            'total_revenue': float(total_revenue),
            'monthly_data': monthly_data
        })
    except Exception as e:
        print(f"Revenue report error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'total_revenue': 0,
            'monthly_data': []
        })

# ---------- Notifications ----------
@app.route('/api/admin/notifications')
def api_notifications():
    try:
        notifications = execute_query("""
            SELECT * FROM notifications 
            WHERE user_type = 'admin' 
            ORDER BY created_at DESC 
            LIMIT 50
        """, fetch=True)
        return jsonify(notifications)
    except Exception as e:
        print(f"Notifications error: {e}")
        return jsonify([])

@app.route('/api/admin/notifications/<int:id>/read', methods=['PUT'])
def api_mark_notification_read(id):
    try:
        execute_query("UPDATE notifications SET is_read = TRUE WHERE notification_id = %s", (id,))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Mark notification read error: {e}")
        return jsonify({'success': False})

# ---------- Activity Log ----------
@app.route('/api/admin/activity')
def api_activity_log():
    try:
        activities = execute_query("""
            SELECT * FROM activity_log 
            WHERE user_type = 'admin' 
            ORDER BY created_at DESC 
            LIMIT 100
        """, fetch=True)
        return jsonify(activities)
    except Exception as e:
        print(f"Activity log error: {e}")
        return jsonify([])

# ---------- Performance Metrics ----------
@app.route('/api/admin/metrics')
def api_performance_metrics():
    """Get performance metrics using optimized queries with pre-calculated values"""
    try:
        # Use customer view which has lifetime_value already calculated by triggers
        total_visitors = execute_query("SELECT COUNT(*) as total_visitors FROM customer", fetch=True)[0]['total_visitors']
        total_orders = execute_query("SELECT COUNT(*) as total_orders FROM orders", fetch=True)[0]['total_orders']
        conversion_rate = (total_orders / total_visitors * 100) if total_visitors > 0 else 0
        
        # Average order value
        avg_order_value = execute_query("SELECT AVG(total_amount) as avg_order_value FROM orders", fetch=True)[0]['avg_order_value'] or 0
        
        # Customer lifetime value (now auto-calculated by triggers)
        avg_lifetime_value = execute_query("SELECT AVG(lifetime_value) as avg_lifetime_value FROM customer WHERE lifetime_value IS NOT NULL", fetch=True)
        avg_lifetime_value = avg_lifetime_value[0]['avg_lifetime_value'] if avg_lifetime_value and avg_lifetime_value[0].get('avg_lifetime_value') else 0
        
        # Recent orders (last 24 hours)
        recent_orders = execute_query("""
            SELECT COUNT(*) as recent_orders 
            FROM orders 
            WHERE order_date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """, fetch=True)[0]['recent_orders']
        
        return jsonify({
            'conversion_rate': round(conversion_rate, 2),
            'avg_order_value': round(float(avg_order_value), 2),
            'avg_lifetime_value': round(float(avg_lifetime_value), 2),
            'recent_orders': recent_orders
        })
    except Exception as e:
        print(f"Performance metrics error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'conversion_rate': 0,
            'avg_order_value': 0,
            'avg_lifetime_value': 0,
            'recent_orders': 0
        })

# ---------- Inventory Alerts ----------
@app.route('/api/admin/inventory-alerts')
def api_inventory_alerts():
    try:
        alerts = execute_query("""
            SELECT ia.*, p.name as product_name 
            FROM inventory_alerts ia
            JOIN product p ON p.product_id = ia.product_id
            WHERE ia.alert_status = 'pending'
            ORDER BY ia.created_at DESC
        """, fetch=True)
        return jsonify(alerts)
    except Exception as e:
        print(f"Inventory alerts error: {e}")
        return jsonify([])

# ---------- Product Analytics ----------
@app.route('/api/admin/products/<int:id>/analytics')
def api_product_analytics(id):
    """Get product analytics using optimized view"""
    try:
        # Use v_product_sales view which has pre-calculated sales data
        analytics = execute_query("""
            SELECT *
            FROM v_product_sales
            WHERE product_id = %s
        """, (id,), fetch=True)
        return jsonify(analytics[0] if analytics else {})
    except Exception as e:
        print(f"Product analytics error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({})

# ---------- Customer Segmentation ----------
@app.route('/api/admin/customers/segments')
def api_customer_segments():
    """Get customer segments using view with pre-calculated segment field"""
    try:
        # Use v_customer_summary view which already has segment calculated
        segments = execute_query("""
            SELECT 
                COALESCE(segment, 'New') as segment, 
                COUNT(*) as count, 
                COALESCE(AVG(lifetime_value), 0) as avg_value,
                COALESCE(SUM(lifetime_value), 0) as total_value,
                COALESCE(AVG(total_orders), 0) as avg_orders
            FROM v_customer_summary 
            GROUP BY segment
            ORDER BY avg_value DESC
        """, fetch=True)
        return jsonify(segments)
    except Exception as e:
        print(f"Customer segments error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/admin/customers/update-segments', methods=['POST'])
def api_update_customer_segments():
    """Manually trigger customer segment update using stored procedure"""
    try:
        execute_query("CALL sp_update_customer_segments()", fetch=False)
        return jsonify({'success': True, 'message': 'Customer segments updated successfully'})
    except Exception as e:
        print(f"Update customer segments error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Order Tracking ----------
@app.route('/api/admin/orders/<int:id>/tracking', methods=['PUT'])
def api_update_order_tracking(id):
    try:
        data = request.json
        execute_query("""
            UPDATE orders 
            SET shipping_status = %s, tracking_number = %s, last_updated = NOW()
            WHERE order_id = %s
        """, (data['shipping_status'], data.get('tracking_number'), id))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update order tracking error: {e}")
        return jsonify({'success': False})

# ---------- Bulk Operations ----------
@app.route('/api/admin/orders/bulk-update', methods=['PUT'])
def api_bulk_update_orders():
    try:
        data = request.json
        order_ids = data['order_ids']
        status = data['status']
        
        placeholders = ','.join(['%s'] * len(order_ids))
        execute_query(f"""
            UPDATE orders 
            SET status = %s, last_updated = NOW()
            WHERE order_id IN ({placeholders})
        """, [status] + order_ids)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Bulk update orders error: {e}")
        return jsonify({'success': False})

# ---------- Returns & Refunds ----------
@app.route('/api/admin/returns', methods=['GET'])
def api_returns():
    try:
        status = request.args.get('status', 'all')
        
        query = """
            SELECT rr.*, o.order_date, c.name as customer_name, p.name as product_name
            FROM returns_refunds rr
            JOIN orders o ON o.order_id = rr.order_id
            JOIN customer c ON c.customer_id = rr.customer_id
            JOIN product p ON p.product_id = rr.product_id
            WHERE 1=1
        """
        params = []
        
        if status != 'all':
            query += " AND rr.status = %s"
            params.append(status)
        
        query += " ORDER BY rr.created_at DESC"
        
        returns = execute_query(query, tuple(params) if params else None, fetch=True)
        return jsonify(returns)
    except Exception as e:
        print(f"Returns error: {e}")
        return jsonify([])

@app.route('/api/admin/returns', methods=['POST'])
def api_create_return():
    try:
        data = request.json
        execute_query("""
            INSERT INTO returns_refunds (order_id, product_id, customer_id, reason, status, refund_amount)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data['order_id'], data['product_id'], data['customer_id'], 
              data['reason'], data['status'], data['refund_amount']))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Create return error: {e}")
        return jsonify({'success': False})

@app.route('/api/admin/returns/<int:id>', methods=['PUT'])
def api_update_return_status(id):
    """Update return/refund status"""
    try:
        data = request.json
        status = data.get('status')
        
        if status not in ['Requested', 'Approved', 'Rejected', 'Refunded']:
            return jsonify({'success': False, 'error': 'Invalid status'})
        
        execute_query(
            "UPDATE returns_refunds SET status = %s WHERE id = %s",
            (status, id)
        )
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update return status error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Advanced Analytics ----------
@app.route('/api/admin/analytics/sales-forecast')
def api_sales_forecast():
    try:
        historical_data = execute_query("""
            SELECT DATE_FORMAT(order_date, '%Y-%m') as month, 
                   SUM(total_amount) as revenue,
                   COUNT(*) as orders
            FROM orders 
            WHERE order_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY month
            ORDER BY month
        """, fetch=True)
        return jsonify(historical_data)
    except Exception as e:
        print(f"Sales forecast error: {e}")
        return jsonify([])

@app.route('/api/admin/analytics/customer-behavior')
def api_customer_behavior():
    try:
        behavior = execute_query("""
            SELECT 
                segment,
                AVG(total_orders) as avg_orders,
                AVG(avg_order_value) as avg_order_value,
                AVG(lifetime_value) as avg_lifetime_value
            FROM customer 
            GROUP BY segment
        """, fetch=True)
        return jsonify(behavior)
    except Exception as e:
        print(f"Customer behavior error: {e}")
        return jsonify([])

# ---------- Bulk Actions ----------
@app.route('/api/admin/bulk/products/delete', methods=['POST'])
def api_bulk_delete_products():
    try:
        data = request.json
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({'success': False, 'error': 'No products selected'})
        
        placeholders = ','.join(['%s'] * len(product_ids))
        execute_query(f"DELETE FROM product WHERE product_id IN ({placeholders})", product_ids)
        
        return jsonify({'success': True, 'deleted_count': len(product_ids)})
    except Exception as e:
        print(f"Bulk delete products error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/bulk/products/update-stock', methods=['POST'])
def api_bulk_update_stock():
    try:
        data = request.json
        updates = data.get('updates', [])
        
        if not updates:
            return jsonify({'success': False, 'error': 'No updates provided'})
        
        for update in updates:
            execute_query(
                "UPDATE product SET quantityavailable = %s WHERE product_id = %s",
                (update['stock'], update['product_id'])
            )
        
        return jsonify({'success': True, 'updated_count': len(updates)})
    except Exception as e:
        print(f"Bulk update stock error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/bulk/orders/update-status', methods=['POST'])
def api_bulk_update_order_status():
    try:
        data = request.json
        order_ids = data.get('order_ids', [])
        status = data.get('status')
        
        if not order_ids or not status:
            return jsonify({'success': False, 'error': 'Missing order IDs or status'})
        
        placeholders = ','.join(['%s'] * len(order_ids))
        execute_query(f"""
            UPDATE orders 
            SET status = %s, last_updated = NOW()
            WHERE order_id IN ({placeholders})
        """, [status] + order_ids)
        
        return jsonify({'success': True, 'updated_count': len(order_ids)})
    except Exception as e:
        print(f"Bulk update order status error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Export Functions ----------
@app.route('/api/admin/export/orders')
def api_export_orders():
    try:
        orders = execute_query("""
            SELECT o.*, c.name as customer_name, c.email, c.phone
            FROM orders o
            LEFT JOIN customer c ON c.customer_id = o.customer_id
            ORDER BY o.order_date DESC
        """, fetch=True)
        return jsonify(orders)
    except Exception as e:
        print(f"Export orders error: {e}")
        return jsonify([])

# ========== NEW ADMIN FEATURES ==========

# ---------- Database Management: Table Structure Viewer ----------
@app.route('/api/admin/db/tables')
def api_get_tables():
    """Get all tables in the database"""
    try:
        tables = execute_query("SHOW TABLES", fetch=True)
        table_names = [list(table.values())[0] for table in tables]
        return jsonify({'success': True, 'tables': table_names})
    except Exception as e:
        print(f"Get tables error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/db/table/<table_name>/structure')
def api_get_table_structure(table_name):
    """Get structure of a specific table"""
    try:
        structure = execute_query(f"DESCRIBE `{table_name}`", fetch=True)
        return jsonify({'success': True, 'structure': structure})
    except Exception as e:
        print(f"Get table structure error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/db/table/<table_name>/data')
def api_get_table_data(table_name):
    """Get data from a specific table with pagination"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        # Get total count
        count_result = execute_query(f"SELECT COUNT(*) as total FROM `{table_name}`", fetch=True)
        total = count_result[0]['total'] if count_result else 0
        
        # Get data
        data = execute_query(f"SELECT * FROM `{table_name}` LIMIT %s OFFSET %s", (limit, offset), fetch=True)
        
        return jsonify({
            'success': True,
            'data': data,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"Get table data error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Database Management: Query Executor ----------
@app.route('/api/admin/db/query', methods=['POST'])
def api_execute_custom_query():
    """Execute custom SQL query (read-only for safety)"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        
        # Security: Only allow SELECT queries
        if not query.upper().startswith('SELECT'):
            return jsonify({'success': False, 'error': 'Only SELECT queries are allowed for security'})
        
        # Prevent dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE']
        query_upper = query.upper()
        if any(keyword in query_upper for keyword in dangerous_keywords):
            return jsonify({'success': False, 'error': 'Query contains prohibited operations'})
        
        result = execute_query(query, fetch=True)
        return jsonify({'success': True, 'data': result, 'count': len(result)})
    except Exception as e:
        print(f"Query execution error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Database Management: Database Statistics ----------
@app.route('/api/admin/db/statistics')
def api_database_statistics():
    """Get comprehensive database statistics"""
    try:
        stats = {}
        
        # Table sizes
        table_sizes = execute_query("""
            SELECT 
                table_name AS 'table',
                ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'size_mb',
                table_rows AS 'rows'
            FROM information_schema.TABLES 
            WHERE table_schema = DATABASE()
            ORDER BY (data_length + index_length) DESC
        """, fetch=True)
        stats['table_sizes'] = table_sizes
        
        # Total database size
        db_size = execute_query("""
            SELECT 
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'db_size_mb'
            FROM information_schema.TABLES 
            WHERE table_schema = DATABASE()
        """, fetch=True)
        stats['database_size_mb'] = db_size[0]['db_size_mb'] if db_size else 0
        
        # Row counts per table
        tables = execute_query("SHOW TABLES", fetch=True)
        table_counts = {}
        for table in tables:
            table_name = list(table.values())[0]
            try:
                count = execute_query(f"SELECT COUNT(*) as count FROM `{table_name}`", fetch=True)
                table_counts[table_name] = count[0]['count'] if count else 0
            except:
                table_counts[table_name] = 0
        stats['table_counts'] = table_counts
        
        return jsonify({'success': True, 'statistics': stats})
    except Exception as e:
        print(f"Database statistics error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Database Management: Health Check ----------
@app.route('/api/admin/db/health')
def api_database_health():
    """Check database health and connection status"""
    try:
        health = {
            'status': 'healthy',
            'connection': False,
            'response_time_ms': 0,
            'active_connections': 0,
            'max_connections': 0,
            'issues': []
        }
        
        import time
        start = time.time()
        test = execute_query("SELECT 1 as test", fetch=True)
        health['response_time_ms'] = round((time.time() - start) * 1000, 2)
        health['connection'] = True if test else False
        
        # Get connection info
        try:
            conn_info = execute_query("SHOW VARIABLES LIKE 'max_connections'", fetch=True)
            if conn_info:
                health['max_connections'] = conn_info[0]['Value']
            
            status = execute_query("SHOW STATUS LIKE 'Threads_connected'", fetch=True)
            if status:
                health['active_connections'] = status[0]['Value']
        except:
            pass
        
        # Check for issues
        if health['response_time_ms'] > 1000:
            health['issues'].append('Slow response time')
        if not health['connection']:
            health['status'] = 'unhealthy'
            health['issues'].append('Connection failed')
        
        return jsonify({'success': True, 'health': health})
    except Exception as e:
        print(f"Database health check error: {e}")
        return jsonify({'success': False, 'error': str(e), 'health': {'status': 'unhealthy'}})

# ---------- Data Import/Export: Export All Data ----------
@app.route('/api/admin/export/all')
def api_export_all_data():
    """Export all data from all tables"""
    try:
        tables = execute_query("SHOW TABLES", fetch=True)
        export_data = {}
        
        for table in tables:
            table_name = list(table.values())[0]
            try:
                data = execute_query(f"SELECT * FROM `{table_name}`", fetch=True)
                export_data[table_name] = data
            except Exception as e:
                export_data[table_name] = {'error': str(e)}
        
        return jsonify({'success': True, 'data': export_data})
    except Exception as e:
        print(f"Export all data error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/export/table/<table_name>')
def api_export_table(table_name):
    """Export data from a specific table"""
    try:
        data = execute_query(f"SELECT * FROM `{table_name}`", fetch=True)
        return jsonify({'success': True, 'table': table_name, 'data': data, 'count': len(data)})
    except Exception as e:
        print(f"Export table error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Data Import: Import CSV Data ----------
@app.route('/api/admin/import/csv', methods=['POST'])
def api_import_csv():
    """Import data from CSV format"""
    try:
        data = request.json
        table_name = data.get('table_name')
        csv_data = data.get('csv_data', [])
        
        if not table_name or not csv_data:
            return jsonify({'success': False, 'error': 'Missing table_name or csv_data'})
        
        if len(csv_data) < 2:
            return jsonify({'success': False, 'error': 'CSV must have headers and at least one row'})
        
        headers = csv_data[0]
        rows = csv_data[1:]
        
        # Build INSERT query
        placeholders = ','.join(['%s'] * len(headers))
        columns = ','.join([f"`{h}`" for h in headers])
        
        inserted = 0
        for row in rows:
            if len(row) == len(headers):
                execute_query(
                    f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})",
                    tuple(row)
                )
                inserted += 1
        
        return jsonify({'success': True, 'inserted': inserted})
    except Exception as e:
        print(f"Import CSV error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Admin User Management ----------
@app.route('/api/admin/users', methods=['GET'])
def api_get_admin_users():
    """Get all admin users"""
    try:
        admins = execute_query("SELECT * FROM admin", fetch=True)
        # Don't return passwords
        for admin in admins:
            admin.pop('password', None)
        return jsonify({'success': True, 'users': admins})
    except Exception as e:
        print(f"Get admin users error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users', methods=['POST'])
def api_create_admin_user():
    """Create a new admin user"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'})
        
        # Check if username exists
        existing = execute_query("SELECT * FROM admin WHERE username=%s", (username,), fetch=True)
        if existing:
            return jsonify({'success': False, 'error': 'Username already exists'})
        
        execute_query(
            "INSERT INTO admin (username, password, email) VALUES (%s, %s, %s)",
            (username, password, email)
        )
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Create admin user error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def api_update_admin_user(user_id):
    """Update admin user"""
    try:
        data = request.json
        updates = []
        params = []
        
        if 'username' in data:
            updates.append("username=%s")
            params.append(data['username'])
        if 'password' in data:
            updates.append("password=%s")
            params.append(data['password'])
        if 'email' in data:
            updates.append("email=%s")
            params.append(data['email'])
        
        if not updates:
            return jsonify({'success': False, 'error': 'No fields to update'})
        
        params.append(user_id)
        query = f"UPDATE admin SET {', '.join(updates)} WHERE admin_id=%s"
        execute_query(query, tuple(params))
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update admin user error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def api_delete_admin_user(user_id):
    """Delete admin user"""
    try:
        execute_query("DELETE FROM admin WHERE admin_id=%s", (user_id,))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete admin user error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Advanced Search: Search Across All Tables ----------
@app.route('/api/admin/search/global', methods=['POST'])
def api_global_search():
    """Search across all tables for a term"""
    try:
        data = request.json
        search_term = data.get('term', '')
        limit = int(data.get('limit', 10))
        
        if not search_term:
            return jsonify({'success': False, 'error': 'Search term required'})
        
        # Get all tables
        tables = execute_query("SHOW TABLES", fetch=True)
        results = {}
        
        for table in tables:
            table_name = list(table.values())[0]
            try:
                # Get column names
                structure = execute_query(f"DESCRIBE `{table_name}`", fetch=True)
                text_columns = [col['Field'] for col in structure if 'varchar' in col['Type'].lower() or 'text' in col['Type'].lower()]
                
                if text_columns:
                    # Build search query
                    conditions = ' OR '.join([f"`{col}` LIKE %s" for col in text_columns])
                    query = f"SELECT * FROM `{table_name}` WHERE {conditions} LIMIT %s"
                    params = tuple(['%' + search_term + '%'] * len(text_columns) + [limit])
                    
                    matches = execute_query(query, params, fetch=True)
                    if matches:
                        results[table_name] = matches
            except Exception as e:
                print(f"Search error in table {table_name}: {e}")
                continue
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        print(f"Global search error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Audit Logs: Enhanced Activity Tracking ----------
@app.route('/api/admin/audit-logs')
def api_audit_logs():
    """Get comprehensive audit logs"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        offset = (page - 1) * limit
        
        # Get activity logs
        logs = execute_query("""
            SELECT * FROM activity_log 
            WHERE user_type = 'admin' 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """, (limit, offset), fetch=True)
        
        # Get total count
        count = execute_query("SELECT COUNT(*) as total FROM activity_log WHERE user_type = 'admin'", fetch=True)
        total = count[0]['total'] if count else 0
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': total,
            'page': page,
            'limit': limit
        })
    except Exception as e:
        print(f"Audit logs error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- System Settings ----------
@app.route('/api/admin/settings', methods=['GET'])
def api_get_settings():
    """Get system settings"""
    try:
        # Check if settings table exists, if not return defaults
        try:
            settings = execute_query("SELECT * FROM settings", fetch=True)
            settings_dict = {s['key']: s['value'] for s in settings} if settings else {}
        except:
            settings_dict = {}
        
        # Default settings
        default_settings = {
            'store_name': settings_dict.get('store_name', 'Cartique'),
            'currency': settings_dict.get('currency', 'INR'),
            'low_stock_threshold': settings_dict.get('low_stock_threshold', '10'),
            'auto_approve_orders': settings_dict.get('auto_approve_orders', 'false'),
            'email_notifications': settings_dict.get('email_notifications', 'true')
        }
        
        return jsonify({'success': True, 'settings': default_settings})
    except Exception as e:
        print(f"Get settings error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/settings', methods=['PUT'])
def api_update_settings():
    """Update system settings"""
    try:
        data = request.json
        
        # Check if settings table exists
        try:
            execute_query("SELECT 1 FROM settings LIMIT 1", fetch=True)
        except:
            # Create settings table if it doesn't exist
            execute_query("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    `key` VARCHAR(100) UNIQUE,
                    value TEXT
                )
            """)
        
        for key, value in data.items():
            # Insert or update
            execute_query("""
                INSERT INTO settings (`key`, value) 
                VALUES (%s, %s) 
                ON DUPLICATE KEY UPDATE value = %s
            """, (key, str(value), str(value)))
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update settings error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Data Validation Tools ----------
@app.route('/api/admin/validate/data')
def api_validate_data():
    """Validate data integrity across tables"""
    try:
        issues = []
        
        # Check for orphaned records
        # Products without valid sellers
        orphaned_products = execute_query("""
            SELECT p.product_id, p.name 
            FROM product p 
            LEFT JOIN seller s ON s.id = p.seller_id 
            WHERE p.seller_id IS NOT NULL AND s.id IS NULL
        """, fetch=True)
        if orphaned_products:
            issues.append({
                'type': 'orphaned_products',
                'message': f'Found {len(orphaned_products)} products with invalid seller references',
                'count': len(orphaned_products)
            })
        
        # Orders without customers
        orphaned_orders = execute_query("""
            SELECT o.order_id 
            FROM orders o 
            LEFT JOIN customer c ON c.customer_id = o.customer_id 
            WHERE o.customer_id IS NOT NULL AND c.customer_id IS NULL
        """, fetch=True)
        if orphaned_orders:
            issues.append({
                'type': 'orphaned_orders',
                'message': f'Found {len(orphaned_orders)} orders with invalid customer references',
                'count': len(orphaned_orders)
            })
        
        # Products with negative stock
        negative_stock = execute_query("""
            SELECT product_id, name, quantityavailable 
            FROM product 
            WHERE quantityavailable < 0
        """, fetch=True)
        if negative_stock:
            issues.append({
                'type': 'negative_stock',
                'message': f'Found {len(negative_stock)} products with negative stock',
                'count': len(negative_stock),
                'products': negative_stock
            })
        
        return jsonify({
            'success': True,
            'issues': issues,
            'status': 'healthy' if not issues else 'issues_found'
        })
    except Exception as e:
        print(f"Data validation error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Database Optimization: Analyze Tables ----------
@app.route('/api/admin/db/optimize', methods=['POST'])
def api_optimize_database():
    """Optimize database tables"""
    try:
        data = request.json
        table_name = data.get('table_name')
        
        if table_name:
            # Optimize specific table
            execute_query(f"OPTIMIZE TABLE `{table_name}`", fetch=True)
            return jsonify({'success': True, 'message': f'Table {table_name} optimized'})
        else:
            # Optimize all tables
            tables = execute_query("SHOW TABLES", fetch=True)
            optimized = []
            for table in tables:
                table_name = list(table.values())[0]
                try:
                    execute_query(f"OPTIMIZE TABLE `{table_name}`", fetch=True)
                    optimized.append(table_name)
                except:
                    pass
            return jsonify({'success': True, 'optimized_tables': optimized})
    except Exception as e:
        print(f"Database optimization error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ========== CLOTHING SHOPPING APP FEATURES ==========

# ---------- Category Management ----------
@app.route('/api/admin/categories', methods=['GET'])
def api_get_categories():
    """Get all product categories with statistics"""
    try:
        categories = execute_query("""
            SELECT 
                category,
                COUNT(*) as product_count,
                SUM(quantityavailable) as total_stock,
                AVG(price) as avg_price,
                SUM(CASE WHEN quantityavailable = 0 THEN 1 ELSE 0 END) as out_of_stock
            FROM product
            GROUP BY category
            ORDER BY product_count DESC
        """, fetch=True)
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"Get categories error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/categories/<category>/products')
def api_get_category_products(category):
    """Get all products in a specific category"""
    try:
        products = execute_query("SELECT * FROM product WHERE category = %s", (category,), fetch=True)
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        print(f"Get category products error: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ---------- Top Customers ----------
@app.route('/api/admin/customers/top')
def api_top_customers():
    """Get top customers using optimized view with pre-calculated values"""
    try:
        limit = int(request.args.get('limit', 10))
        # Use v_customer_summary view which has all stats pre-calculated
        customers = execute_query("""
            SELECT *
            FROM v_customer_summary
            WHERE lifetime_value > 0
            ORDER BY lifetime_value DESC
            LIMIT %s
        """, (limit,), fetch=True)
        return jsonify({'success': True, 'customers': customers})
    except Exception as e:
        print(f"Top customers error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ---------- Customer Purchase History ----------
@app.route('/api/admin/customers/<int:customer_id>/history')
def api_customer_history(customer_id):
    """Get complete purchase history using optimized view"""
    try:
        # Use v_order_details view
        orders = execute_query("""
            SELECT *, DATE_FORMAT(order_date, '%Y-%m-%d %H:%i') as formatted_date
            FROM v_order_details
            WHERE customer_id = %s
            ORDER BY order_date DESC
        """, (customer_id,), fetch=True)
        
        # Create items array from order data
        for order in orders:
            if order.get('product_id') and order.get('product_name'):
                order['items'] = [{
                    'product_name': order.get('product_name', 'N/A'),
                    'category': order.get('product_category', 'N/A'),
                    'qty': 1,  # Default quantity
                    'price': float(order.get('product_price', order.get('total_amount', 0)))
                }]
            else:
                order['items'] = []
        
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        print(f"Customer history error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/customers/<int:customer_id>/stats')
def api_customer_stats(customer_id):
    """Get detailed customer statistics using stored procedure"""
    try:
        stats = execute_query("CALL sp_get_customer_stats(%s)", (customer_id,), fetch=True)
        if stats and len(stats) > 0:
            return jsonify({'success': True, 'stats': stats[0]})
        else:
            return jsonify({'success': False, 'error': 'Customer not found'})
    except Exception as e:
        print(f"Customer stats error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Reviews Management ----------
@app.route('/api/admin/reviews', methods=['GET'])
def api_get_reviews():
    """Get all product reviews"""
    try:
        product_id = request.args.get('product_id')
        status = request.args.get('status', 'all')  # all, approved, pending
        
        query = """
            SELECT 
                r.*,
                p.name as product_name,
                c.name as customer_name,
                DATE_FORMAT(r.created_at, '%Y-%m-%d') as review_date
            FROM reviews r
            JOIN product p ON p.product_id = r.product_id
            JOIN customer c ON c.customer_id = r.customer_id
            WHERE 1=1
        """
        params = []
        
        if product_id:
            query += " AND r.product_id = %s"
            params.append(int(product_id))
        
        if status != 'all':
            query += " AND r.status = %s"
            params.append(status)
        
        query += " ORDER BY r.created_at DESC"
        
        reviews = execute_query(query, tuple(params) if params else None, fetch=True)
        return jsonify({'success': True, 'reviews': reviews})
    except Exception as e:
        print(f"Get reviews error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/reviews/<int:review_id>', methods=['PUT'])
def api_update_review(review_id):
    """Update review status (approve/reject)"""
    try:
        data = request.json
        status = data.get('status')  # approved, rejected, pending
        
        execute_query("UPDATE reviews SET status = %s WHERE review_id = %s", (status, review_id))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update review error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/reviews/<int:review_id>', methods=['DELETE'])
def api_delete_review(review_id):
    """Delete a review"""
    try:
        execute_query("DELETE FROM reviews WHERE review_id = %s", (review_id,))
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete review error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Discounts & Coupons ----------
@app.route('/api/admin/coupons', methods=['GET'])
def api_get_coupons():
    """Get all discount coupons"""
    try:
        coupons = execute_query("SELECT * FROM coupons ORDER BY created_at DESC", fetch=True)
        return jsonify({'success': True, 'coupons': coupons})
    except Exception as e:
        # If table doesn't exist, return empty
        return jsonify({'success': True, 'coupons': []})

@app.route('/api/admin/coupons', methods=['POST'])
def api_create_coupon():
    """Create a new discount coupon"""
    try:
        data = request.json
        code = data.get('code')
        discount_type = data.get('discount_type', 'percentage')  # percentage or fixed
        discount_value = data.get('discount_value')
        min_purchase = data.get('min_purchase', 0)
        max_discount = data.get('max_discount')
        valid_from = data.get('valid_from')
        valid_until = data.get('valid_until')
        usage_limit = data.get('usage_limit')
        
        # Check if coupons table exists, create if not
        try:
            execute_query("SELECT 1 FROM coupons LIMIT 1", fetch=True)
        except:
            execute_query("""
                CREATE TABLE IF NOT EXISTS coupons (
                    coupon_id INT AUTO_INCREMENT PRIMARY KEY,
                    code VARCHAR(50) UNIQUE,
                    discount_type VARCHAR(20),
                    discount_value DECIMAL(10,2),
                    min_purchase DECIMAL(10,2) DEFAULT 0,
                    max_discount DECIMAL(10,2),
                    valid_from DATE,
                    valid_until DATE,
                    usage_limit INT,
                    used_count INT DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        execute_query("""
            INSERT INTO coupons (code, discount_type, discount_value, min_purchase, max_discount, valid_from, valid_until, usage_limit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (code, discount_type, discount_value, min_purchase, max_discount, valid_from, valid_until, usage_limit))
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Create coupon error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/coupons/<int:coupon_id>', methods=['PUT'])
def api_update_coupon(coupon_id):
    """Update coupon"""
    try:
        data = request.json
        updates = []
        params = []
        
        for key in ['status', 'discount_value', 'usage_limit']:
            if key in data:
                updates.append(f"{key} = %s")
                params.append(data[key])
        
        if updates:
            params.append(coupon_id)
            execute_query(f"UPDATE coupons SET {', '.join(updates)} WHERE coupon_id = %s", tuple(params))
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Update coupon error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Low Stock Alerts ----------
@app.route('/api/admin/inventory/low-stock')
def api_low_stock_products():
    """Get products with low stock"""
    try:
        threshold = int(request.args.get('threshold', 10))
        products = execute_query("""
            SELECT 
                product_id,
                name,
                category,
                quantityavailable,
                price
            FROM product
            WHERE quantityavailable <= %s
            ORDER BY quantityavailable ASC
            LIMIT 20
        """, (threshold,), fetch=True)
        return jsonify({'success': True, 'products': products, 'count': len(products)})
    except Exception as e:
        print(f"Low stock products error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Pending Orders ----------
@app.route('/api/admin/orders/pending')
def api_pending_orders():
    """Get all pending orders"""
    try:
        orders = execute_query("""
            SELECT 
                o.*,
                c.name as customer_name,
                c.email as customer_email,
                DATE_FORMAT(o.order_date, '%Y-%m-%d %H:%i') as formatted_date
            FROM orders o
            LEFT JOIN customer c ON c.customer_id = o.customer_id
            WHERE o.status = 'Pending'
            ORDER BY o.order_date DESC
            LIMIT 20
        """, fetch=True)
        return jsonify({'success': True, 'orders': orders, 'count': len(orders)})
    except Exception as e:
        print(f"Pending orders error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Daily Sales Report ----------
@app.route('/api/admin/reports/daily-sales')
def api_daily_sales():
    """Get daily sales using optimized view"""
    try:
        days = int(request.args.get('days', 30))
        # Use v_daily_sales view for better performance
        sales = execute_query("""
            SELECT *
            FROM v_daily_sales
            WHERE sale_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY sale_date DESC
        """, (days,), fetch=True)
        return jsonify({'success': True, 'sales': sales})
    except Exception as e:
        print(f"Daily sales error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ---------- Product Performance by Category ----------
@app.route('/api/admin/analytics/category-performance')
def api_category_performance():
    """Get performance metrics by category using optimized view"""
    try:
        # Use v_product_sales view for aggregated product data
        performance = execute_query("""
            SELECT 
                category,
                COUNT(DISTINCT product_id) as total_products,
                SUM(quantityavailable) as total_stock,
                SUM(CASE WHEN quantityavailable = 0 THEN 1 ELSE 0 END) as out_of_stock,
                COALESCE(SUM(total_orders), 0) as total_sold,
                COALESCE(SUM(total_revenue), 0) as revenue,
                AVG(price) as avg_price
            FROM v_product_sales
            GROUP BY category
            ORDER BY revenue DESC
        """, fetch=True)
        return jsonify({'success': True, 'performance': performance})
    except Exception as e:
        print(f"Category performance error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ---------- Recent Orders Summary ----------
@app.route('/api/admin/orders/recent')
def api_recent_orders():
    """Get recent orders using optimized view"""
    try:
        limit = int(request.args.get('limit', 20))
        # Use v_order_details view for better performance
        orders = execute_query("""
            SELECT *, DATE_FORMAT(order_date, '%Y-%m-%d %H:%i') as formatted_date
            FROM v_order_details
            ORDER BY order_date DESC
            LIMIT %s
        """, (limit,), fetch=True)
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        print(f"Recent orders error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ---------- Product Search with Filters ----------
@app.route('/api/admin/products/search')
def api_search_products():
    """Advanced product search with multiple filters"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        min_price = request.args.get('min_price')
        max_price = request.args.get('max_price')
        in_stock = request.args.get('in_stock')
        
        sql = "SELECT * FROM product WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (name LIKE %s OR description LIKE %s)"
            params.extend([f'%{query}%', f'%{query}%'])
        
        if category:
            sql += " AND category = %s"
            params.append(category)
        
        if min_price:
            sql += " AND price >= %s"
            params.append(float(min_price))
        
        if max_price:
            sql += " AND price <= %s"
            params.append(float(max_price))
        
        if in_stock == 'true':
            sql += " AND quantityavailable > 0"
        elif in_stock == 'false':
            sql += " AND quantityavailable = 0"
        
        sql += " ORDER BY product_id DESC"
        
        products = execute_query(sql, tuple(params) if params else None, fetch=True)
        return jsonify({'success': True, 'products': products, 'count': len(products)})
    except Exception as e:
        print(f"Product search error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- Shipping Status Overview ----------
@app.route('/api/admin/orders/shipping-status-overview')
def api_shipping_status_overview():
    """Get shipping status overview for analytics"""
    try:
        overview = execute_query("""
            SELECT 
                COALESCE(shipping_status, 'Pending') as shipping_status,
                COUNT(*) as count,
                SUM(total_amount) as total_value
            FROM orders
            GROUP BY shipping_status
            ORDER BY 
                CASE shipping_status
                    WHEN 'Pending' THEN 1
                    WHEN 'Shipped' THEN 2
                    WHEN 'Delivered' THEN 3
                    WHEN 'Returned' THEN 4
                    ELSE 5
                END
        """, fetch=True)
        return jsonify({'success': True, 'overview': overview})
    except Exception as e:
        print(f"Shipping status overview error: {e}")
        return jsonify({'success': False, 'error': str(e), 'overview': []})

# ---------- Order Statistics ----------
@app.route('/api/admin/orders/statistics')
def api_order_statistics():
    """Get comprehensive order statistics"""
    try:
        stats = {}
        
        # Total orders
        total_orders = execute_query("SELECT COUNT(*) as total FROM orders", fetch=True)[0]['total']
        stats['total_orders'] = total_orders
        
        # Orders by status
        orders_by_status = execute_query("""
            SELECT status, COUNT(*) as count
            FROM orders
            GROUP BY status
        """, fetch=True)
        stats['by_status'] = orders_by_status
        
        # Average order value
        avg_order = execute_query("SELECT AVG(total_amount) as avg FROM orders", fetch=True)[0]['avg'] or 0
        stats['avg_order_value'] = float(avg_order)
        
        # Orders today
        orders_today = execute_query("""
            SELECT COUNT(*) as total FROM orders 
            WHERE DATE(order_date) = CURDATE()
        """, fetch=True)[0]['total']
        stats['orders_today'] = orders_today
        
        # Revenue today
        revenue_today = execute_query("""
            SELECT COALESCE(SUM(total_amount), 0) as total FROM orders 
            WHERE DATE(order_date) = CURDATE()
        """, fetch=True)[0]['total']
        stats['revenue_today'] = float(revenue_today)
        
        return jsonify({'success': True, 'statistics': stats})
    except Exception as e:
        print(f"Order statistics error: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ---------- PDF Bill Generation ----------
@app.route('/api/admin/bills/<int:order_id>/pdf')
def api_generate_bill_pdf(order_id):
    """Generate PDF bill for an order"""
    try:
        # Get order details using optimized view
        order = execute_query("""
            SELECT *, DATE_FORMAT(order_date, '%Y-%m-%d %H:%i') as formatted_date
            FROM v_order_details
            WHERE order_id = %s
        """, (order_id,), fetch=True)
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        order = order[0]
        
        # Create items array from order data (since product_id is now in orders table)
        items = []
        if order.get('product_id') and order.get('product_name'):
            items = [{
                'product_name': order.get('product_name', 'N/A'),
                'category': order.get('product_category', 'N/A'),
                'qty': 1,  # Default quantity
                'price': float(order.get('total_amount', 0))
            }]
        
        # Generate HTML for PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Invoice #{order_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #333; margin: 0; }}
                .info {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
                .info div {{ flex: 1; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .total {{ text-align: right; font-size: 18px; font-weight: bold; margin-top: 20px; }}
                .footer {{ margin-top: 40px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧵 Cartique</h1>
                <h2>Invoice</h2>
            </div>
            <div class="info">
                <div>
                    <strong>Bill To:</strong><br>
                    {order.get('customer_name', 'N/A')}<br>
                    {order.get('customer_email', 'N/A')}<br>
                    {order.get('customer_phone', 'N/A')}<br>
                    {order.get('address', '')}
                </div>
                <div style="text-align: right;">
                    <strong>Invoice #:</strong> {order_id}<br>
                    <strong>Date:</strong> {order.get('formatted_date', 'N/A')}<br>
                    <strong>Status:</strong> {order.get('status', 'N/A')}
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Category</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for item in items:
            item_total = float(item.get('price', 0)) * int(item.get('qty', 1))
            html_content += f"""
                    <tr>
                        <td>{item.get('product_name', 'N/A')}</td>
                        <td>{item.get('category', 'N/A')}</td>
                        <td>{item.get('qty', 1)}</td>
                        <td>₹{float(item.get('price', 0)):,.2f}</td>
                        <td>₹{item_total:,.2f}</td>
                    </tr>
            """
        
        html_content += f"""
                </tbody>
            </table>
            <div class="total">
                <strong>Grand Total: ₹{float(order.get('total_amount', 0)):,.2f}</strong>
            </div>
            <div class="footer">
                <p>Thank you for your business!</p>
                <p>This is a computer-generated invoice.</p>
            </div>
        </body>
        </html>
        """
        
        # Return HTML (browser will handle PDF generation via print)
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        print(f"PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ---------- Run App ----------
if __name__ == '__main__':
    app.run(debug=True)
