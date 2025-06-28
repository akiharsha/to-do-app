import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import sqlite3
from datetime import datetime
import csv
from tkcalendar import DateEntry

# === Database Setup ===
conn = sqlite3.connect("tasks.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        due_date TEXT,
        priority INTEGER
    )
""")
conn.commit()

class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("To-Do List with SQLite")
        self.dark_mode = False

        # === Entry Frame ===
        self.entry_frame = ttk.Frame(root)
        self.entry_frame.pack(pady=10)

        ttk.Label(self.entry_frame, text="Task").grid(row=0, column=0)
        ttk.Label(self.entry_frame, text="Due Date").grid(row=0, column=1)
        ttk.Label(self.entry_frame, text="Priority (1=High, 2=Med, 3=Low)").grid(row=0, column=2)

        self.task_entry = ttk.Entry(self.entry_frame, width=30)
        self.task_entry.grid(row=1, column=0, padx=5)

        self.due_entry = DateEntry(self.entry_frame, width=16, date_pattern='yyyy-MM-dd')
        self.due_entry.grid(row=1, column=1, padx=5)

        self.priority_entry = ttk.Entry(self.entry_frame, width=8)
        self.priority_entry.grid(row=1, column=2, padx=5)

        self.add_button = ttk.Button(self.entry_frame, text="Add Task", command=self.add_task)
        self.add_button.grid(row=1, column=3, padx=5)

        # === Listbox with Scrollbar ===
        self.list_frame = ttk.Frame(root)
        self.list_frame.pack(pady=10)

        self.tasks_listbox = tk.Listbox(self.list_frame, width=80, height=12)
        self.tasks_listbox.pack(side=tk.LEFT, fill=tk.BOTH)

        self.scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tasks_listbox.yview)
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        self.tasks_listbox.config(yscrollcommand=self.scrollbar.set)

        # === Buttons Frame ===
        self.buttons_frame = ttk.Frame(root)
        self.buttons_frame.pack(pady=5)

        self.done_button = ttk.Button(self.buttons_frame, text="Toggle Done", command=self.toggle_done)
        self.done_button.grid(row=0, column=0, padx=5)

        self.delete_button = ttk.Button(self.buttons_frame, text="Delete Task", command=self.delete_task)
        self.delete_button.grid(row=0, column=1, padx=5)

        self.export_button = ttk.Button(self.buttons_frame, text="Export CSV", command=self.export_csv)
        self.export_button.grid(row=0, column=2, padx=5)

        self.dark_button = ttk.Button(self.buttons_frame, text="Toggle Dark Mode", command=self.toggle_dark_mode)
        self.dark_button.grid(row=0, column=3, padx=5)

        # === Filter Buttons ===
        self.filter_frame = ttk.Frame(root)
        self.filter_frame.pack(pady=5)

        ttk.Button(self.filter_frame, text="All", command=lambda: self.refresh_tasks()).pack(side=tk.LEFT, padx=3)
        ttk.Button(self.filter_frame, text="Pending", command=lambda: self.refresh_tasks(filter_done=0)).pack(side=tk.LEFT, padx=3)
        ttk.Button(self.filter_frame, text="Completed", command=lambda: self.refresh_tasks(filter_done=1)).pack(side=tk.LEFT, padx=3)

        self.refresh_tasks()
        self.check_reminders()

    def add_task(self):
        task = self.task_entry.get().strip()
        due_date = self.due_entry.get_date().strftime("%Y-%m-%d")
        priority = self.priority_entry.get().strip()

        if not task:
            messagebox.showwarning("Input error", "Task cannot be empty.")
            return

        if priority not in ["1", "2", "3"]:
            messagebox.showwarning("Priority error", "Priority must be 1, 2, or 3.")
            return

        cursor.execute("INSERT INTO tasks (task, due_date, priority) VALUES (?, ?, ?)", (task, due_date, int(priority)))
        conn.commit()

        self.task_entry.delete(0, tk.END)
        self.priority_entry.delete(0, tk.END)
        self.due_entry.set_date(datetime.today())

        self.refresh_tasks()

    def refresh_tasks(self, filter_done=None):
        self.tasks_listbox.delete(0, tk.END)
        query = "SELECT id, task, done, due_date, priority FROM tasks"
        params = ()
        if filter_done in (0, 1):
            query += " WHERE done = ?"
            params = (filter_done,)
        query += " ORDER BY priority, due_date"

        cursor.execute(query, params)
        self.task_data = cursor.fetchall()

        for task in self.task_data:
            id_, text, done, due, priority = task
            status = "✓" if done else " "
            due_display = due if due else "No due date"
            display = f"[{status}] {text} (Due: {due_display}, Priority: {priority})"
            self.tasks_listbox.insert(tk.END, display)

    def toggle_done(self):
        selected = self.tasks_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Select a task to mark done/undone.")
            return

        index = selected[0]
        task_id, done = self.task_data[index][0], self.task_data[index][2]

        cursor.execute("UPDATE tasks SET done = ? WHERE id = ?", (0 if done else 1, task_id))
        conn.commit()
        self.refresh_tasks()

    def delete_task(self):
        selected = self.tasks_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Select a task to delete.")
            return

        index = selected[0]
        task_id = self.task_data[index][0]

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        self.refresh_tasks()

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not filepath:
            return

        cursor.execute("SELECT task, done, due_date, priority FROM tasks ORDER BY priority, due_date")
        rows = cursor.fetchall()

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Task", "Completed", "Due Date", "Priority"])
            for task, done, due_date, priority in rows:
                writer.writerow([task, "Yes" if done else "No", due_date or "", priority])

        messagebox.showinfo("Exported", f"Tasks exported to {filepath}")

    def toggle_dark_mode(self):
        if not self.dark_mode:
            bg_color = "#222222"  # Darker background
            fg_color = "#dddddd"  # Light text
            entry_bg = "#333333"
            entry_fg = "#ffffff"
            listbox_bg = "#121212"
            listbox_fg = "#eeeeee"
            btn_bg = "#444444"
            btn_fg = "#ffffff"
        else:
            # Light mode colors (defaults)
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            entry_bg = "white"
            entry_fg = "black"
            listbox_bg = "white"
            listbox_fg = "black"
            btn_bg = None
            btn_fg = None

        self.root.configure(bg=bg_color)

        def recursive_configure(widget):
            for child in widget.winfo_children():
                cls = child.winfo_class()

                if cls in ("Frame", "Labelframe"):
                    child.configure(bg=bg_color)
                    recursive_configure(child)

                elif cls == "Label":
                    child.configure(bg=bg_color, fg=fg_color)

                elif cls == "Button":
                    if btn_bg:
                        child.configure(bg=btn_bg, fg=btn_fg, activebackground=btn_bg, activeforeground=btn_fg)
                    else:
                        # Reset to default
                        child.configure(bg="SystemButtonFace", fg="SystemButtonText")

                elif cls == "Entry":
                    child.configure(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)

                elif cls == "Listbox":
                    child.configure(bg=listbox_bg, fg=listbox_fg, selectbackground="#555555", selectforeground=listbox_fg)

                elif cls == "TCombobox":  # For ttk widgets like DateEntry’s internal combobox
                    try:
                        child.configure(background=entry_bg, foreground=entry_fg)
                    except:
                        pass

                else:
                    # For other widget types, try to set bg/fg, ignore errors
                    try:
                        child.configure(bg=bg_color, fg=fg_color)
                    except:
                        pass

                # Recursively go deeper
                recursive_configure(child)

        recursive_configure(self.root)
        self.dark_mode = not self.dark_mode


    def check_reminders(self):
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("SELECT task, due_date FROM tasks WHERE done=0 AND due_date IS NOT NULL AND due_date <= ?", (today,))
        rows = cursor.fetchall()
        for task, due in rows:
            messagebox.showwarning("Reminder", f"⚠️ Task due: '{task}' (Due: {due})")
        self.root.after(3600000, self.check_reminders)  # recheck every hour

if __name__ == "__main__":
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()
