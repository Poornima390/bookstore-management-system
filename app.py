from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ---------------- DATABASE CONNECTION ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="MYSQLroot@2005",
    database="bookstore"
)


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form["role"]
        username = request.form["username"]
        password = request.form["password"]

        if role == "admin" and username == "admin" and password == "admin123":
            session.clear()
            session["role"] = "admin"
            return redirect("/dashboard")

        elif role == "staff" and username == "staff" and password == "staff123":
            session.clear()
            session["role"] = "staff"
            session["cart"] = []
            return redirect("/dashboard")

        else:
            flash("Invalid Role, Username or Password!")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if "role" not in session:
        return redirect("/")

    cursor = db.cursor(dictionary=True)


    # -------- ADMIN --------
    if session["role"] == "admin":

        cursor.execute("SELECT COUNT(*) as total FROM books")
        total_books = cursor.fetchone()["total"]

        cursor.execute("SELECT SUM(total_amount) as earnings FROM bills")
        result = cursor.fetchone()
        earnings = result["earnings"] if result["earnings"] else 0

        cursor.execute("SELECT COUNT(*) as bills FROM bills")
        total_bills = cursor.fetchone()["bills"]

        cursor.execute("""
            SELECT COUNT(*) as low_stock
            FROM books
            WHERE stock < 5 AND stock > 0
        """)
        low_stock = cursor.fetchone()["low_stock"]

        cursor.execute("""
            SELECT COUNT(*) as out_stock
            FROM books
            WHERE stock=0
        """)
        out_stock = cursor.fetchone()["out_stock"]


        cursor.execute("""
            SELECT books.title,
                   SUM(bill_items.quantity) as sold
            FROM bill_items
            JOIN books
            ON books.id=bill_items.book_id
            GROUP BY bill_items.book_id
            ORDER BY sold DESC
            LIMIT 1
        """)
        top_book = cursor.fetchone()

        if top_book:
            best_selling = top_book["title"]
        else:
            best_selling = "No Sales"


        # GRAPH DATA
        cursor.execute("""
            SELECT MONTHNAME(bill_date) as month,
                   SUM(total_amount) as sales
            FROM bills
            GROUP BY MONTH(bill_date), MONTHNAME(bill_date)
            ORDER BY MONTH(bill_date)
        """)

        rows = cursor.fetchall()

        months = []
        sales = []

        for row in rows:
            months.append(row["month"])
            sales.append(float(row["sales"]))


        cursor.close()

        return render_template(
            "admin_dashboard.html",
            total_books=total_books,
            earnings=earnings,
            total_bills=total_bills,
            low_stock=low_stock,
            out_stock=out_stock,
            best_selling=best_selling,
            months=months,
            sales=sales
        )


    # -------- STAFF --------

    cursor.execute("""
        SELECT COUNT(*) as total
        FROM books
    """)
    total_books = cursor.fetchone()["total"]


    cursor.execute("""
        SELECT COUNT(*) as bills_today
        FROM bills
        WHERE DATE(bill_date)=CURDATE()
    """)
    bills_today = cursor.fetchone()["bills_today"]


    cursor.execute("""
        SELECT SUM(total_amount) as sales_today
        FROM bills
        WHERE DATE(bill_date)=CURDATE()
    """)
    result = cursor.fetchone()
    sales_today = result["sales_today"] if result["sales_today"] else 0


    cursor.execute("""
        SELECT COUNT(*) as low_stock
        FROM books
        WHERE stock < 5 AND stock > 0
    """)
    low_stock = cursor.fetchone()["low_stock"]


    # GRAPH DATA
    cursor.execute("""
        SELECT MONTHNAME(bill_date) as month,
               SUM(total_amount) as sales
        FROM bills
        GROUP BY MONTH(bill_date), MONTHNAME(bill_date)
        ORDER BY MONTH(bill_date)
    """)

    rows = cursor.fetchall()

    months = []
    sales = []

    for row in rows:
        months.append(row["month"])
        sales.append(float(row["sales"]))


    cursor.close()

    return render_template(
        "staff_dashboard.html",
        total_books=total_books,
        bills_today=bills_today,
        sales_today=sales_today,
        low_stock=low_stock,
        months=months,
        sales=sales
    )

# ---------------- MANAGE BOOKS ----------------
@app.route("/books")
def books():
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM books ORDER BY title ASC")
    books = cursor.fetchall()
    cursor.close()

    return render_template("books.html", books=books)


@app.route("/delete_book/<int:id>")
def delete_book(id):
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor()
    cursor.execute("DELETE FROM books WHERE id=%s", (id,))
    db.commit()
    cursor.close()

    flash("Book deleted successfully!")
    return redirect("/books")


# ---------------- ADD BOOK ----------------
@app.route("/add_book", methods=["POST"])
def add_book():
    if session.get("role") != "admin":
        return redirect("/")

    title = request.form["title"]
    author = request.form["author"]
    price = request.form["price"]
    stock = request.form["stock"]

    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, price, stock) VALUES (%s,%s,%s,%s)",
        (title, author, price, stock)
    )
    db.commit()
    cursor.close()

    flash("Book Added Successfully!")
    return redirect("/books")


@app.route("/edit_book/<int:id>")
def edit_book(id):
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM books WHERE id=%s", (id,))
    book = cursor.fetchone()
    cursor.close()

    return render_template("edit_book.html", book=book)


@app.route("/update_book/<int:id>", methods=["POST"])
def update_book(id):
    if session.get("role") != "admin":
        return redirect("/")

    title = request.form["title"]
    author = request.form["author"]
    price = request.form["price"]
    stock = request.form["stock"]

    cursor = db.cursor()
    cursor.execute("""
        UPDATE books
        SET title=%s, author=%s, price=%s, stock=%s
        WHERE id=%s
    """, (title, author, price, stock, id))
    db.commit()
    cursor.close()

    flash("Book Updated Successfully!")
    return redirect("/books")


# ---------------- ADD TO CART ----------------
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    if session.get("role") != "staff":
        return redirect("/")

    book_id = request.form["book_id"]
    quantity = int(request.form["quantity"])

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM books WHERE id=%s", (book_id,))
    book = cursor.fetchone()
    cursor.close()

    if not book:
        flash("Book not found!")
        return redirect("/generate_bill")

    if quantity > book["stock"]:
        flash("Not enough stock!")
        return redirect("/generate_bill")

    item = {
        "book_id": book["id"],
        "title": book["title"],
        "price": book["price"],
        "quantity": quantity,
        "total": book["price"] * quantity
    }

    cart = session.get("cart", [])
    cart.append(item)
    session["cart"] = cart
    session.modified = True

    flash("Book added to bill!")
    return redirect("/generate_bill")


# ---------------- GENERATE BILL ----------------
@app.route("/generate_bill")
def generate_bill():
    if session.get("role") != "staff":
        return redirect("/")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM books ORDER BY title ASC")
    books = cursor.fetchall()
    cursor.close()

    cart = session.get("cart", [])
    total = sum(item["total"] for item in cart)

    return render_template("generate_bill.html",
                           books=books,
                           cart=cart,
                           total=total)


# ---------------- FINALIZE BILL ----------------
@app.route("/finalize_bill", methods=["POST"])
def finalize_bill():
    if session.get("role") != "staff":
        return redirect("/")

    customer_name = request.form["customer_name"]
    phone = request.form["phone"]

    cart = session.get("cart", [])

    if not cart:
        flash("Cart is empty!")
        return redirect("/generate_bill")

    total_amount = sum(item["total"] for item in cart)

    cursor = db.cursor()

    # Insert bill
    cursor.execute(
        "INSERT INTO bills (customer_name, phone, total_amount) VALUES (%s,%s,%s)",
        (customer_name, phone, total_amount)
    )
    db.commit()

    bill_id = cursor.lastrowid

    # Insert bill items (FIXED PART)
    for item in cart:
        cursor.execute(
            """INSERT INTO bill_items 
               (bill_id, book_id, book_title, quantity, price, total) 
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (
                bill_id,
                item["book_id"],
                item["title"],
                item["quantity"],
                item["price"],
                item["total"]
            )
        )

        cursor.execute(
            "UPDATE books SET stock = stock - %s WHERE id=%s",
            (item["quantity"], item["book_id"])
        )

    db.commit()
    cursor.close()

    session["cart"] = []

    return redirect(url_for("print_bill", bill_id=bill_id))


# ---------------- PRINT BILL ----------------
@app.route("/print_bill/<int:bill_id>")
def print_bill(bill_id):
    if session.get("role") != "staff":
        return redirect("/")

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM bills WHERE id=%s", (bill_id,))
    bill = cursor.fetchone()

    cursor.execute("SELECT * FROM bill_items WHERE bill_id=%s", (bill_id,))
    items = cursor.fetchall()

    cursor.close()

    return render_template("print_bill.html",
                           bill=bill,
                           items=items)


# ---------------- VIEW BILLS ----------------
@app.route("/view_bills")
def view_bills():
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM bills ORDER BY bill_date DESC")
    bills = cursor.fetchall()
    cursor.close()

    return render_template("view_bills.html", bills=bills)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
