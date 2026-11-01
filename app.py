
import streamlit as st
import sqlite3
from datetime import date, timedelta

# DATABASE CONNECTION
conn = sqlite3.connect("library.db", check_same_thread=False)
cursor = conn.cursor()

# CREATE TABLES
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    author TEXT,
    quantity INTEGER,
    available INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    member_type TEXT,
    email TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER,
    member_id INTEGER,
    issue_date TEXT,
    due_date TEXT,
    return_date TEXT,
    fine INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Issued'
)
""")

conn.commit()

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Library Management System",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Library Management System")
st.write("Manage Books, Members, Issues and Returns")

# SIDEBAR
menu = st.sidebar.selectbox(
    "Select Option",
    [
        "Dashboard",
        "Add Book",
        "View Books",
        "Delete Book",
        "Register Member",
        "View Members",
        "Issue Book",
        "Return Book",
        "Overdue Books"
    ]
)

# DASHBOARD
if menu == "Dashboard":

    st.header("Dashboard")

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM members")
    total_members = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM loans WHERE status='Issued'"
    )
    issued_books = cursor.fetchone()[0]

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Books", total_books)
    c2.metric("Total Members", total_members)
    c3.metric("Issued Books", issued_books)


# ADD BOOK
elif menu == "Add Book":

    st.header("Add New Book")

    title = st.text_input("Book Title")
    author = st.text_input("Author")
    quantity = st.number_input(
        "Quantity", min_value=1, step=1
    )

    if st.button("Add Book"):

        if title and author:

            cursor.execute("""
            INSERT INTO books
            (title, author, quantity, available)
            VALUES (?, ?, ?, ?)
            """, (title, author, quantity, quantity))

            conn.commit()

            st.success("Book Added Successfully!")

        else:
            st.error("Please enter book title and author.")


# VIEW BOOKS
elif menu == "View Books":

    st.header("Available Books")

    search = st.text_input("Search by title or author")

    cursor.execute("""
    SELECT * FROM books
    WHERE title LIKE ? OR author LIKE ?
    """, ('%' + search + '%', '%' + search + '%'))

    books = cursor.fetchall()

    st.table([
        {
            "ID": b[0],
            "Title": b[1],
            "Author": b[2],
            "Quantity": b[3],
            "Available": b[4]
        }
        for b in books
    ])


# DELETE BOOK
elif menu == "Delete Book":

    st.header("Delete Book")

    cursor.execute("SELECT id, title FROM books")
    books = cursor.fetchall()

    if books:

        selected = st.selectbox(
            "Select Book",
            books,
            format_func=lambda x: f"{x[0]} - {x[1]}"
        )

        if st.button("Delete"):

            cursor.execute("""
            SELECT COUNT(*) FROM loans
            WHERE book_id=? AND status='Issued'
            """, (selected[0],))

            if cursor.fetchone()[0] > 0:
                st.error("Return issued copies before deleting this book.")
            else:
                cursor.execute(
                    "DELETE FROM books WHERE id=?",
                    (selected[0],)
                )
                conn.commit()
                st.success("Book Deleted Successfully!")
    else:
        st.info("No books available.")


# REGISTER MEMBER
elif menu == "Register Member":

    st.header("Register New Member")

    name = st.text_input("Member Name")

    member_type = st.selectbox(
        "Member Type",
        ["Student", "Teacher"]
    )

    email = st.text_input("Email")

    if st.button("Register Member"):

        if name:

            cursor.execute("""
            INSERT INTO members
            (name, member_type, email)
            VALUES (?, ?, ?)
            """, (name, member_type, email))

            conn.commit()

            st.success("Member Registered Successfully!")

        else:
            st.error("Enter member name.")


# VIEW MEMBERS
elif menu == "View Members":

    st.header("Registered Members")

    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()

    st.table([
        {
            "ID": m[0],
            "Name": m[1],
            "Type": m[2],
            "Email": m[3]
        }
        for m in members
    ])


# ISSUE BOOK
elif menu == "Issue Book":

    st.header("Issue a Book")

    cursor.execute(
        "SELECT id, title, available FROM books WHERE available > 0"
    )
    books = cursor.fetchall()

    cursor.execute(
        "SELECT id, name, member_type FROM members"
    )
    members = cursor.fetchall()

    if books and members:

        selected_book = st.selectbox(
            "Select Book",
            books,
            format_func=lambda x: x[1]
        )

        selected_member = st.selectbox(
            "Select Member",
            members,
            format_func=lambda x: f"{x[1]} ({x[2]})"
        )

        loan_days = st.number_input(
            "Loan Period (Days)",
            min_value=1,
            value=14
        )

        if st.button("Issue Book"):

            member_id = selected_member[0]
            member_type = selected_member[2]

            limit = 3 if member_type == "Student" else 5

            cursor.execute("""
            SELECT COUNT(*) FROM loans
            WHERE member_id=? AND status='Issued'
            """, (member_id,))

            current_loans = cursor.fetchone()[0]

            if current_loans >= limit:

                st.error("Member borrowing limit reached!")

            else:

                issue_date = date.today()
                due_date = issue_date + timedelta(days=loan_days)

                cursor.execute("""
                INSERT INTO loans
                (book_id, member_id, issue_date, due_date)
                VALUES (?, ?, ?, ?)
                """, (
                    selected_book[0],
                    member_id,
                    str(issue_date),
                    str(due_date)
                ))

                cursor.execute("""
                UPDATE books
                SET available = available - 1
                WHERE id=?
                """, (selected_book[0],))

                conn.commit()

                st.success(
                    f"Book issued! Due date: {due_date}"
                )

    else:
        st.warning("Add books and register members first.")


# RETURN BOOK
elif menu == "Return Book":

    st.header("Return a Book")

    cursor.execute("""
    SELECT loans.id, books.title, members.name,
           loans.due_date, loans.book_id
    FROM loans
    JOIN books ON loans.book_id = books.id
    JOIN members ON loans.member_id = members.id
    WHERE loans.status='Issued'
    """)

    loans = cursor.fetchall()

    if loans:

        selected_loan = st.selectbox(
            "Select Loan",
            loans,
            format_func=lambda x:
            f"{x[1]} - {x[2]} (Due: {x[3]})"
        )

        if st.button("Return Book"):

            return_date = date.today()
            due_date = date.fromisoformat(selected_loan[3])

            late_days = max(
                (return_date - due_date).days, 0
            )

            fine = late_days * 10

            cursor.execute("""
            UPDATE loans
            SET status='Returned',
                return_date=?,
                fine=?
            WHERE id=?
            """, (
                str(return_date),
                fine,
                selected_loan[0]
            ))

            cursor.execute("""
            UPDATE books
            SET available = available + 1
            WHERE id=?
            """, (selected_loan[4],))

            conn.commit()

            st.success("Book Returned Successfully!")
            st.info(f"Late Fine: PKR {fine}")

    else:
        st.info("No issued books available for return.")


# OVERDUE BOOKS
elif menu == "Overdue Books":

    st.header("Overdue Books")

    cursor.execute("""
    SELECT books.title, members.name,
           loans.due_date
    FROM loans
    JOIN books ON loans.book_id = books.id
    JOIN members ON loans.member_id = members.id
    WHERE loans.status='Issued'
    AND loans.due_date < ?
    """, (str(date.today()),))

    overdue = cursor.fetchall()

    if overdue:

        for book in overdue:

            due = date.fromisoformat(book[2])
            days = (date.today() - due).days
            fine = days * 10

            st.warning(
                f"Book: {book[0]} | Member: {book[1]} | "
                f"Due: {due} | Days Late: {days} | "
                f"Estimated Fine: PKR {fine}"
            )

    else:
        st.success("No Overdue Books!")


