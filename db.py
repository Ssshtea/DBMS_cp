import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',  
    database='clothing_store'
)
cursor = conn.cursor(buffered=True)

def show_products():
    cursor.execute("SELECT product_id, name, description, price, category, quantityavailable FROM product")
    products = cursor.fetchall()
    print("\n--- Products ---")
    for p in products:
        print(f"ID: {p[0]}, Name: {p[1]}, Desc: {p[2]}, Price: {p[3]}, Category: {p[4]}, Stock: {p[5]}")

def view_orders(customer_id):
    cursor.execute("SELECT order_id, order_date, total_amount, status FROM orders WHERE customer_id=%s", (customer_id,))
    orders = cursor.fetchall()
    print(f"\n--- Orders for Customer {customer_id} ---")
    for o in orders:
        print(f"Order ID: {o[0]}, Date: {o[1]}, Total: {o[2]}, Status: {o[3]}")

def add_review(customer_id):
    product_id = int(input("Enter Product ID to review: "))
    rating = int(input("Enter rating (1-5): "))
    comment = input("Enter comment: ")
    cursor.execute("INSERT INTO reviews (customer_id, product_id, rating, comment) VALUES (%s,%s,%s,%s)",
                   (customer_id, product_id, rating, comment))
    conn.commit()
    print("Review added successfully!")

def place_order(customer_id):
    product_id = int(input("Enter Product ID to buy: "))
    quantity = int(input("Enter quantity: "))
    # Get product price
    cursor.execute("SELECT price, quantityavailable FROM product WHERE product_id=%s", (product_id,))
    result = cursor.fetchone()
    if not result:
        print("Product not found!")
        return
    price, stock = result
    if quantity > stock:
        print(f"Only {stock} items available!")
        return
    total = price * quantity
    # Insert into orders
    cursor.execute("INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES (%s, CURDATE(), %s, 'Pending')",
                   (customer_id, total))
    conn.commit()
    order_id = cursor.lastrowid
    # Insert into payments
    cursor.execute("INSERT INTO payments (order_id, payment_date, payment_method, amount) VALUES (%s, CURDATE(), 'Credit Card', %s)",
                   (order_id, total))
    # Update product stock
    cursor.execute("UPDATE product SET quantityavailable=quantityavailable-%s WHERE product_id=%s", (quantity, product_id))
    conn.commit()
    print(f"Order placed successfully! Order ID: {order_id}, Total: {total}")

def admin_dashboard():
    cursor.execute("SELECT COUNT(*) FROM product")
    total_products = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total_amount) FROM orders")
    total_revenue = cursor.fetchone()[0]
    print(f"\n--- Admin Dashboard ---\nTotal Products: {total_products}\nTotal Orders: {total_orders}\nTotal Revenue: {total_revenue}")

def manage_products():
    print("\n1. Add Product\n2. Update Product\n3. Delete Product")
    choice = input("Choose: ")
    if choice == '1':
        name = input("Name: ")
        desc = input("Description: ")
        price = float(input("Price: "))
        category = input("Category: ")
        qty = int(input("Quantity: "))
        cursor.execute("INSERT INTO product (name, description, price, category, quantityavailable) VALUES (%s,%s,%s,%s,%s)",
                       (name, desc, price, category, qty))
        conn.commit()
        print("Product added.")
    elif choice == '2':
        pid = int(input("Product ID to update: "))
        price = float(input("New Price: "))
        qty = int(input("New Quantity: "))
        cursor.execute("UPDATE product SET price=%s, quantityavailable=%s WHERE product_id=%s", (price, qty, pid))
        conn.commit()
        print("Product updated.")
    elif choice == '3':
        pid = int(input("Product ID to delete: "))
        cursor.execute("DELETE FROM product WHERE product_id=%s", (pid,))
        conn.commit()
        print("Product deleted.")

def main():
    while True:
        print("\n--- Main Menu ---\n1. Customer Panel\n2. Admin Panel\n3. Exit")
        choice = input("Choose: ")
        if choice == '1':
            customer_id = int(input("Enter Customer ID: "))
            while True:
                print("\nCustomer Menu\n1. Show Products\n2. Place Order\n3. View Orders\n4. Add Review\n5. Back")
                c = input("Choose: ")
                if c == '1':
                    show_products()
                elif c == '2':
                    place_order(customer_id)
                elif c == '3':
                    view_orders(customer_id)
                elif c == '4':
                    add_review(customer_id)
                elif c == '5':
                    break
                else:
                    print("Invalid choice.")
        elif choice == '2':
            while True:
                print("\nAdmin Menu\n1. Dashboard\n2. Manage Products\n3. Back")
                a = input("Choose: ")
                if a == '1':
                    admin_dashboard()
                elif a == '2':
                    manage_products()
                elif a == '3':
                    break
                else:
                    print("Invalid choice.")
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")

# Run the program
main()
conn.close()
