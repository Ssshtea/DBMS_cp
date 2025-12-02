<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">

</head>
<body>

<h1>🛍️ Cartique – Clothing Store DBMS Project</h1>
<p>A full-stack Database Management System project featuring MySQL, Flask, triggers, procedures, views, and analytics.</p>

<hr>

<div class="section">
    <h2>🚀 Project Overview</h2>
    <p>This project simulates a real e-commerce clothing store with an advanced DBMS backend.</p>
    <ul>
        <li>Product Management</li>
        <li>Order Placement & Automatic Inventory Updates</li>
        <li>Customer Analytics</li>
        <li>Returns & Refunds System</li>
        <li>Notifications & Activity Logs</li>
        <li>Stored Procedures, Triggers, Views</li>
    </ul>
</div>

<div class="section">
    <h2>📁 Project Structure</h2>
    <div class="file-structure">
<pre>
📦 Cartique-DBMS
│
├── app.py
├── db.py
├── database_improvements.sql
├── DBMS_CONCEPTS_DOCUMENTATION.md
├── templates/
│   └── index.html
└── static/
     └── app,js
     └── styles.css
  
</pre>
    </div>
</div>

<div class="section">
    <h2>🛠️ Prerequisites</h2>

   <h3>1️⃣ Python 3.8+</h3>
    <p>Install required packages:</p>
    <pre>pip install flask mysql-connector-python</pre>

   <h3>2️⃣ MySQL Server</h3>
    <p>Database credentials used in this project:</p>
    <pre>
host: localhost  
user: root  
password: root  
database: clothing_store
    </pre>

  <h3>3️⃣ Create Database</h3>
    <pre>
CREATE DATABASE clothing_store;
USE clothing_store;
    </pre>
</div>

<div class="section">
    <h2>🧱 Step 1 — Import Tables</h2>
    <p>Import your base schema OR create tables manually.</p>
</div>

<div class="section">
    <h2>🧠 Step 2 — Apply Advanced Database Logic</h2>
    <p>Run:</p>
    <pre>database_improvements.sql</pre>

   <p>This adds triggers, procedures, views, and automation.</p>

  <pre>
mysql -u root -p clothing_store < database_improvements.sql
    </pre>
</div>

<div class="section">
    <h2>🖥️ Step 3 — Run Flask Backend</h2>
    <pre>python app.py</pre>
</div>

<div class="section">
    <h2>👨‍💻 Step 4 — Run CLI Interface</h2>
    <pre>python db.py</pre>
</div>

<div class="section">
    <h2>📌 Example Commands</h2>

  <div class="code-title">Test database connection:</div>
    <pre>http://localhost:5000/api/test-db</pre>

  <div class="code-title">Access admin panel:</div>
    <pre>http://localhost:5000/admin</pre>
</div>

<div class="section">
    <h2>📌 DBMS Concepts Implemented</h2>
    <ul>
        <li>Triggers</li>
        <li>Stored Procedures</li>
        <li>Views</li>
        <li>Connection Pooling</li>
        <li>Transactions (COMMIT + ROLLBACK)</li>
        <li>Joins, Aggregation, Grouping</li>
        <li>Parameterized Queries</li>
    </ul>
</div>

<hr>



</body>
</html>

