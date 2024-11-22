import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import json
import subprocess
import platform

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.title("File Content Copier")
        self.geometry("800x600")
        self.node_paths = {}
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.last_working_dir = config.get('last_working_dir', os.getcwd())
                self.last_used_text = config.get('last_used_text', self.get_default_text())
        except FileNotFoundError:
            self.last_working_dir = os.getcwd()
            self.last_used_text = self.get_default_text()

    def save_config(self):
        config = {
            'last_working_dir': self.last_working_dir,
            'last_used_text': self.textarea.get("1.0", tk.END)
        }
        with open('config.json', 'w') as f:
            json.dump(config, f)

    def get_default_text(self):
        return """Use the following context to answer question at the end:

{REPEATABLE_CONTEXT}
"""

    def on_closing(self):
        self.save_config()
        self.destroy()

    def create_widgets(self):
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=1)
        left_frame = tk.Frame(paned)
        paned.add(left_frame)
        right_frame = tk.Frame(paned)
        paned.add(right_frame)
        self.tree = ttk.Treeview(left_frame, columns=("checked",), selectmode="none")
        self.tree.heading("#0", text="File/Folder", anchor='w')
        self.tree.heading("checked", text="Select", anchor='center')
        self.tree.column("#0", stretch=True)
        self.tree.column("checked", width=70, anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=1)
        self.build_tree()
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.copy_button = tk.Button(left_frame, text="Copy to clipboard", command=self.copy_to_clipboard)
        self.copy_button.pack(pady=5)
        self.choose_dir_button = tk.Button(right_frame, text="Choose root dir", command=self.choose_root_directory)
        self.choose_dir_button.pack(pady=5)
        self.textarea = ScrolledText(right_frame)
        self.textarea.pack(fill=tk.BOTH, expand=1)
        self.textarea.insert(tk.END, self.last_used_text)

    def choose_root_directory(self):
        new_dir = filedialog.askdirectory(initialdir=self.last_working_dir)
        if new_dir:
            self.last_working_dir = new_dir
            self.build_tree()

    def build_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.insert_node('', self.last_working_dir, lazy_load=True)

    def insert_node(self, parent, path, lazy_load=False):
        if not os.path.basename(path).startswith('.'):
            text = os.path.basename(path) if os.path.basename(path) else path
            checked_state = "[ ]"
            node = self.tree.insert(parent, 'end', text=text, values=(checked_state,), open=False)
            self.tree.set(node, 'checked', checked_state)
            self.node_paths[node] = path
            if os.path.isdir(path) and lazy_load:
                self.tree.insert(node, 'end', text='dummy')

    def on_tree_expand(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        children = self.tree.get_children(item_id)
        if len(children) == 1 and self.tree.item(children[0], 'text') == 'dummy':
            self.tree.delete(children[0])
            path = self.node_paths.get(item_id)
            if path:
                self.insert_children(item_id, path)

    def insert_children(self, parent, path):
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if not item.startswith('.') and (os.path.isdir(item_path) or self.is_text_file(item_path)):
                    if item_path not in self.node_paths.values():  # Avoid adding duplicate nodes
                        self.insert_node(parent, item_path, lazy_load=True)
        except PermissionError:
            pass

    def is_text_file(self, path):
        # Check if the file is a text file or a code file by its extension
        text_file_extensions = ['.txt', '.py', '.java', '.js', '.html', '.css', '.md', '.json', '.xml', '.csv', '.yaml', '.yml', '.cpp', '.h', '.c', '.sh']
        return os.path.isfile(path) and any(path.lower().endswith(ext) for ext in text_file_extensions)

    def on_tree_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Toggle Selection", command=lambda: self.toggle_selection(item_id))
        menu.add_command(label="Expand/Collapse", command=lambda: self.expand_collapse_node(item_id))
        menu.add_command(label="Open in Explorer", command=lambda: self.open_in_explorer(item_id))
        menu.post(event.x_root, event.y_root)

    def open_in_explorer(self, item_id):
        if item_id not in self.node_paths:
            return
        path = self.node_paths[item_id]
        if os.path.isdir(path) or os.path.isfile(path):
            try:
                if platform.system() == "Windows":
                    os.startfile(path)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.Popen(["open", path])
                else:  # Linux and others
                    subprocess.Popen(["xdg-open", path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open the directory: {e}")

    def toggle_selection(self, item_id):
        if item_id not in self.node_paths:
            return
        current_state = self.tree.set(item_id, 'checked')
        new_state = '[x]' if current_state == '[ ]' else '[ ]'
        self.tree.set(item_id, 'checked', new_state)
        path = self.node_paths[item_id]
        if os.path.isdir(path):
            self.toggle_children(item_id, new_state)

    def toggle_children(self, parent, state):
        for child in self.tree.get_children(parent):
            if child in self.node_paths:
                self.tree.set(child, 'checked', state)
                if os.path.isdir(self.node_paths[child]):
                    self.toggle_children(child, state)

    def expand_collapse_node(self, item_id):
        if self.tree.item(item_id, "open"):
            self.tree.item(item_id, open=False)
        else:
            self.tree.item(item_id, open=True)
            children = self.tree.get_children(item_id)
            if len(children) == 1 and self.tree.item(children[0], 'text') == 'dummy':
                self.tree.delete(children[0])
                path = self.node_paths.get(item_id)
                if path:
                    self.insert_children(item_id, path)

    def copy_to_clipboard(self):
        selected_files = []
        self.get_checked_files('', selected_files)
        if not selected_files:
            messagebox.showwarning("No files selected", "Please select files or folders to copy.")
            return
        content = ''
        for file_path in selected_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                rel_path = os.path.relpath(file_path, self.last_working_dir)
                content += f"------\nFile path: {rel_path}\nFile content:\n{file_content}\n"
            except Exception as e:
                content += f"------\nFile path: {file_path}\nCould not read file: {e}\n------\n"
        new_content = self.textarea.get("1.0", tk.END).replace("{REPEATABLE_CONTEXT}", content)
        self.clipboard_clear()
        self.clipboard_append(new_content)
        messagebox.showinfo("Success", "Content copied to clipboard.")

    def get_checked_files(self, parent, selected_files):
        for child in self.tree.get_children(parent):
            if child in self.node_paths and self.tree.set(child, 'checked') == '[x]':
                path = self.node_paths[child]
                if os.path.isfile(path) and self.is_text_file(path):
                    selected_files.append(path)
                elif os.path.isdir(path):
                    self.collect_files_in_directory(path, selected_files)
            self.get_checked_files(child, selected_files)

    def collect_files_in_directory(self, directory, selected_files):
        for root, _, files in os.walk(directory):
            for file in files:
                if not file.startswith('.'):  # Skip hidden files
                    file_path = os.path.join(root, file)
                    if self.is_text_file(file_path):
                        selected_files.append(file_path)

if __name__ == "__main__":
    app = Application()
    app.mainloop()
