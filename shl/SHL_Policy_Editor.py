import json
import tkinter as tk
from tkinter import ttk

POLICY_FILE = "../shl-policy-config.json"

def load_policy():
    with open(POLICY_FILE, "r") as f:
        return json.load(f)

def save_policy(data):
    with open(POLICY_FILE, "w") as f:
        json.dump(data, f, indent=4)

policy = load_policy()

root = tk.Tk()
root.title("SHL Policy Editor")
root.geometry("1200x700")

# --- Layout ---
main_frame = tk.PanedWindow(root, orient=tk.HORIZONTAL)
main_frame.pack(fill="both", expand=True)

left_frame = tk.Frame(main_frame)
right_frame = tk.Frame(main_frame, padx=20, pady=20)

# Tämä tekee editorista skaalautuvan automaattisesti
main_frame.add(left_frame, stretch="always")
main_frame.add(right_frame, stretch="always")

# --- Treeview ---
tree = ttk.Treeview(
    left_frame,
    columns=("provider", "enabled", "priority", "timeout"),
    show="headings",
    selectmode="browse"
)

tree.heading("provider", text="Provider")
tree.heading("enabled", text="Enabled")
tree.heading("priority", text="Priority")
tree.heading("timeout", text="Timeout")

# Keskitetään sarakkeet
tree.column("provider", anchor="w", width=200)
tree.column("enabled", anchor="center", width=100)
tree.column("priority", anchor="center", width=100)
tree.column("timeout", anchor="center", width=100)

tree.pack(fill="both", expand=True)

# Täytä providerit priority-järjestyksessä
providers_sorted = sorted(policy.items(), key=lambda x: x[1]["priority"])
for name, cfg in providers_sorted:
    tree.insert("", "end", iid=name,
                values=(name, cfg["enabled"], cfg["priority"], cfg["timeout"]))

# --- Drag-and-drop ---
dragging_item = None

def on_button_press(event):
    global dragging_item
    dragging_item = tree.identify_row(event.y)

def on_motion(event):
    global dragging_item
    if dragging_item:
        target = tree.identify_row(event.y)
        if target and target != dragging_item:
            items = list(tree.get_children())
            tree.move(dragging_item, "", items.index(target))

def on_button_release(event):
    global dragging_item
    if dragging_item:
        items = list(tree.get_children())
        for idx, iid in enumerate(items):
            policy[iid]["priority"] = idx + 1
            tree.item(iid, values=(iid, policy[iid]["enabled"], policy[iid]["priority"], policy[iid]["timeout"]))
        save_policy(policy)
    dragging_item = None

tree.bind("<ButtonPress-1>", on_button_press)
tree.bind("<B1-Motion>", on_motion)
tree.bind("<ButtonRelease-1>", on_button_release)

# --- Editoripaneeli (skaalautuu mukana) ---
tk.Label(right_frame, text="Provider Editor", font=("Arial", 18, "bold")).pack(anchor="nw", pady=(0,20))

current_provider = None

# Enabled
tk.Label(right_frame, text="Enabled", font=("Arial", 12)).pack(anchor="nw")
enabled_var = tk.BooleanVar()
tk.Checkbutton(right_frame, variable=enabled_var, font=("Arial", 12)).pack(anchor="nw", pady=(0,10))

# Timeout
tk.Label(right_frame, text="Timeout", font=("Arial", 12)).pack(anchor="nw")
timeout_var = tk.IntVar()
tk.Entry(right_frame, textvariable=timeout_var, width=25, font=("Arial", 12)).pack(anchor="nw", pady=(0,20))

# Allow tags
tk.Label(right_frame, text="Allow Tags", font=("Arial", 12)).pack(anchor="nw")
allow_box = tk.Listbox(right_frame, selectmode="multiple", height=8, width=40, font=("Arial", 12))
allow_box.pack(anchor="nw", pady=(0,20))

# Deny tags
tk.Label(right_frame, text="Deny Tags", font=("Arial", 12)).pack(anchor="nw")
deny_box = tk.Listbox(right_frame, selectmode="multiple", height=8, width=40, font=("Arial", 12))
deny_box.pack(anchor="nw", pady=(0,20))

# --- Providerin valinta ---
def on_select(event):
    global current_provider
    item = tree.selection()[0]
    current_provider = item
    cfg = policy[item]

    enabled_var.set(cfg["enabled"])
    timeout_var.set(cfg["timeout"])

    allow_box.delete(0, "end")
    for tag in cfg.get("allow", []):
        allow_box.insert("end", tag)
        allow_box.selection_set("end")

    deny_box.delete(0, "end")
    for tag in cfg.get("deny", []):
        deny_box.insert("end", tag)
        deny_box.selection_set("end")

tree.bind("<<TreeviewSelect>>", on_select)

# --- Save ---
def save_changes():
    if not current_provider:
        return

    cfg = policy[current_provider]

    cfg["enabled"] = enabled_var.get()
    cfg["timeout"] = timeout_var.get()
    cfg["allow"] = [allow_box.get(i) for i in allow_box.curselection()]
    cfg["deny"] = [deny_box.get(i) for i in deny_box.curselection()]

    save_policy(policy)

    tree.item(current_provider, values=(
        current_provider,
        cfg["enabled"],
        cfg["priority"],
        cfg["timeout"]
    ))

tk.Button(right_frame, text="Save", font=("Arial", 14), width=15, command=save_changes).pack(anchor="nw", pady=20)

root.mainloop()

