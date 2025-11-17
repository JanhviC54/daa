# doctor_scheduler_project_ready.py
# Upgraded version: Admin vs Receptionist, CSV export, daily summary, color-coded priorities, scheduling, Gantt chart

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import matplotlib.pyplot as plt
import datetime
from datetime import timedelta
import csv

# Priority values for sorting
PRIORITY_VALUE = {"High": 3, "Medium": 2, "Low": 1}
PRIORITY_COLOR = {"Emergency": "red", "High": "orange", "Medium": "yellow", "Low": "green"}

# -------------------- Functions --------------------
def sort_patients(patients):
    return sorted(
        patients,
        key=lambda p: (
            0 if p.get("emergency", False) else 1,
            -PRIORITY_VALUE.get(p.get("priority", "Medium"), 2),
            -p.get("time", 0),
        ),
    )

def greedy_schedule_availability(patients, doctors, base_dt):
    sorted_pats = sort_patients(patients)
    unassigned = []

    for d in doctors:
        if "available_from" not in d or d["available_from"] is None:
            d["available_from"] = base_dt.time()
        if "available_to" not in d or d["available_to"] is None:
            d["available_to"] = (base_dt + timedelta(hours=8)).time()
        d["available_from_dt"] = datetime.datetime.combine(base_dt.date(), d["available_from"])
        d["available_to_dt"] = datetime.datetime.combine(base_dt.date(), d["available_to"])
        if d["available_to_dt"] <= d["available_from_dt"]:
            d["available_to_dt"] += timedelta(days=1)
        d["next_free_dt"] = d["available_from_dt"]
        d["appointments"] = []

    for p in sorted_pats:
        assigned = False
        for d in sorted(doctors, key=lambda x: x["next_free_dt"]):
            start_dt = d["next_free_dt"]
            end_dt = start_dt + timedelta(minutes=int(p["time"]))
            if end_dt <= d["available_to_dt"]:
                d["appointments"].append({
                    "name": p["name"],
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "priority": p["priority"],
                    "emergency": p["emergency"],
                    "time": p["time"]
                })
                d["next_free_dt"] = end_dt
                assigned = True
                break
        if not assigned:
            unassigned.append(p)
    return doctors, unassigned

def plot_gantt(doctors, base_dt):
    if not doctors:
        messagebox.showinfo("No data", "No scheduled doctors to plot.")
        return
    fig, ax = plt.subplots(figsize=(10, max(3, len(doctors) * 0.6)))
    cmap = plt.cm.get_cmap("tab20").colors
    for i, d in enumerate(doctors):
        for j, appt in enumerate(d.get("appointments", [])):
            start = (appt["start_dt"] - base_dt).total_seconds() / 60.0
            end = (appt["end_dt"] - base_dt).total_seconds() / 60.0
            color = "red" if appt.get("emergency", False) else cmap[j % len(cmap)]
            ax.barh(i, end - start, left=start, height=0.5, color=color)
            label = f"{appt['name']} ({appt['start_dt'].strftime('%I:%M %p').lstrip('0')})"
            ax.text(start + (end - start)/2, i, label, ha="center", va="center", color="white", fontsize=8)
    ax.set_yticks(range(len(doctors)))
    ax.set_yticklabels([d["name"] for d in doctors])
    ax.set_xlabel("Minutes since clinic start")
    ax.set_title("Doctor Schedule (Emergency = red)")
    plt.tight_layout()
    plt.show()

# -------------------- Main App Class --------------------
class SchedulerAppProject:
    def __init__(self, root):
        self.root = root
        self.root.title("Doctor Scheduling Project Ready")
        self.root.geometry("1000x750")
        self.base_dt = self.auto_base_time()
        self.patients = []
        self.doctors = []
        self.last_scheduled = None
        self.role = None
        self.select_role()
        self.build_ui()

    def auto_base_time(self):
        today = datetime.date.today()
        wd = today.weekday()
        hour = 9 if wd <= 4 else 12
        return datetime.datetime.combine(today, datetime.time(hour=hour))

    def select_role(self):
        role = simpledialog.askstring("Role Selection", "Enter role: Admin or Receptionist").strip().lower()
        if role not in ["admin", "receptionist"]:
            messagebox.showerror("Invalid Role", "Role must be Admin or Receptionist")
            self.root.destroy()
            return
        self.role = role

    def build_ui(self):
        top = tk.Frame(self.root, bg="#0B5FA4", pady=10)
        top.pack(fill="x")
        tk.Label(top, text=f"Doctor Scheduling ({self.role.capitalize()})", fg="white", bg="#0B5FA4",
                 font=("Helvetica", 16, "bold")).pack()
        tk.Label(top, text=f"Clinic start time today: {self.base_dt.strftime('%A %d %b %Y %I:%M %p').lstrip('0')}",
                 fg="white", bg="#0B5FA4").pack()

        main = tk.Frame(self.root, bg="#F7FAFB", padx=10, pady=10)
        main.pack(fill="both", expand=True)
        left = tk.Frame(main, bg="#F7FAFB")
        left.pack(side="left", fill="y", padx=(0,10))
        right = tk.Frame(main, bg="#F7FAFB")
        right.pack(side="left", fill="both", expand=True)

        # Doctors (Admin only)
        doc_frame = tk.LabelFrame(left, text="Doctors", bg="#F7FAFB", padx=6, pady=6)
        doc_frame.pack(fill="x")
        tk.Label(doc_frame, text="Doctor Names (comma separated):", bg="#F7FAFB").grid(row=0, column=0, sticky="w")
        self.doc_names_entry = tk.Entry(doc_frame, width=35)
        self.doc_names_entry.insert(0, "Dr. A, Dr. B, Dr. C")
        self.doc_names_entry.grid(row=1, column=0, pady=4)
        if self.role == "admin":
            tk.Button(doc_frame, text="Set Availability", command=self.set_availability).grid(row=2, column=0, pady=5)
        else:
            tk.Label(doc_frame, text="(Receptionist cannot edit doctors)", bg="#F7FAFB").grid(row=2,column=0)

        # Patients
        pat_frame = tk.LabelFrame(left, text="Add Patient", bg="#F7FAFB", padx=6, pady=6)
        pat_frame.pack(fill="x", pady=(10,0))
        tk.Label(pat_frame, text="Name:", bg="#F7FAFB").grid(row=0, column=0, sticky="w")
        self.p_name = tk.Entry(pat_frame, width=20)
        self.p_name.grid(row=0, column=1)
        tk.Label(pat_frame, text="Time (min):", bg="#F7FAFB").grid(row=1, column=0, sticky="w")
        self.p_time = tk.Entry(pat_frame, width=10)
        self.p_time.grid(row=1, column=1)
        tk.Label(pat_frame, text="Priority:", bg="#F7FAFB").grid(row=2, column=0, sticky="w")
        self.p_priority = ttk.Combobox(pat_frame, values=["High","Medium","Low"], state="readonly", width=10)
        self.p_priority.current(1)
        self.p_priority.grid(row=2, column=1)
        self.p_emergency_var = tk.BooleanVar()
        tk.Checkbutton(pat_frame, text="Emergency", variable=self.p_emergency_var, bg="#F7FAFB").grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Button(pat_frame, text="Add Patient", command=self.add_patient).grid(row=4, column=0, columnspan=2, pady=5)

        # Patients Table
        pat_table_frame = tk.LabelFrame(left, text="Patients", bg="#F7FAFB")
        pat_table_frame.pack(fill="both", expand=True, pady=(10,0))
        cols = ("Name","Time","Priority","Emergency")
        self.p_table = ttk.Treeview(pat_table_frame, columns=cols, show="headings", height=10)
        for c in cols:
            self.p_table.heading(c,text=c)
        self.p_table.column("Name", width=120)
        self.p_table.column("Time", width=60, anchor="center")
        self.p_table.column("Priority", width=80, anchor="center")
        self.p_table.column("Emergency", width=80, anchor="center")
        self.p_table.pack(fill="both", expand=True)
        ttk.Button(left, text="Remove Selected", command=self.remove_patient).pack(pady=(5,0))
        ttk.Button(left, text="Clear All", command=self.clear_all).pack()

        # Schedule output
        sched_frame = tk.LabelFrame(right, text="Final Schedule", bg="#F7FAFB")
        sched_frame.pack(fill="both", expand=True)
        scol = ("Doctor","Patient","Start","End","Priority","Emergency")
        self.s_table = ttk.Treeview(sched_frame, columns=scol, show="headings")
        for c in scol:
            self.s_table.heading(c,text=c)
            self.s_table.column(c,width=120)
        self.s_table.pack(fill="both", expand=True)
        ttk.Button(right, text="Schedule Now", command=self.schedule).pack(pady=5)
        ttk.Button(right, text="Show Gantt", command=self.show_gantt).pack(pady=2)
        ttk.Button(right, text="Export CSV", command=self.export_csv).pack(pady=2)
        ttk.Button(right, text="Show Daily Summary", command=self.show_summary).pack(pady=2)

    # -------------------- Functions --------------------
    def parse_doc_names_to_default_doctors(self):
        names = [n.strip() for n in self.doc_names_entry.get().split(",") if n.strip()]
        if not names:
            names = ["Doctor 1"]
        self.doctors = []
        for n in names:
            self.doctors.append({"name": n, "available_from": self.base_dt.time(), "available_to": (self.base_dt+timedelta(hours=8)).time()})

    def set_availability(self):
        names = [n.strip() for n in self.doc_names_entry.get().split(",") if n.strip()]
        if not names: return
        win = tk.Toplevel(self.root)
        win.title("Set Doctor Availability")
        tk.Label(win,text="Set available times (HH:MM 24-hour)").pack(pady=4)
        frm = tk.Frame(win)
        frm.pack(padx=8,pady=8)
        entries = []
        for i,name in enumerate(names):
            tk.Label(frm,text=name).grid(row=i,column=0)
            e_from = tk.Entry(frm,width=8); e_from.insert(0,self.base_dt.strftime("%H:%M")); e_from.grid(row=i,column=1)
            e_to = tk.Entry(frm,width=8); e_to.insert(0,(self.base_dt+timedelta(hours=8)).strftime("%H:%M")); e_to.grid(row=i,column=2)
            entries.append((name,e_from,e_to))
        def save():
            new_docs = []
            for name,e_from,e_to in entries:
                try:
                    tfrom = datetime.datetime.strptime(e_from.get().strip(),"%H:%M").time()
                    tto = datetime.datetime.strptime(e_to.get().strip(),"%H:%M").time()
                except:
                    messagebox.showerror("Error",f"Invalid time for {name}")
                    return
                new_docs.append({"name":name,"available_from":tfrom,"available_to":tto})
            self.doctors = new_docs
            win.destroy(); messagebox.showinfo("Saved","Doctor availability saved.")
        ttk.Button(win,text="Save",command=save).pack(pady=6)

    def add_patient(self):
        name = self.p_name.get().strip()
        time_str = self.p_time.get().strip()
        priority = self.p_priority.get() or "Medium"
        emergency = bool(self.p_emergency_var.get())
        if not name or not time_str: return
        try: t=int(time_str); assert t>0
        except: messagebox.showwarning("Input","Time must be positive integer"); return
        p = {"name":name,"time":t,"priority":priority,"emergency":emergency}
        self.patients.append(p)
        self.p_table.insert("", "end", values=(p["name"],p["time"],p["priority"],"Yes" if p["emergency"] else "No"), tags=("emergency",) if emergency else ())
        self.p_name.delete(0,tk.END); self.p_time.delete(0,tk.END); self.p_emergency_var.set(False); self.p_priority.current(1)

    def remove_patient(self):
        sel = self.p_table.selection()
        for iid in sel:
            vals = self.p_table.item(iid,"values")
            name = vals[0]
            for p in self.patients:
                if p["name"]==name and str(p["time"])==str(vals[1]): self.patients.remove(p); break
            self.p_table.delete(iid)

    def clear_all(self):
        self.patients.clear()
        for t in self.p_table.get_children(): self.p_table.delete(t)
        for t in self.s_table.get_children(): self.s_table.delete(t)
        self.last_scheduled=None

    def schedule(self):
        if not self.doctors: self.parse_doc_names_to_default_doctors()
        if not self.doctors or not self.patients: return
        for t in self.s_table.get_children(): self.s_table.delete(t)
        docs_copy = [dict(d) for d in self.doctors]
        scheduled, unassigned = greedy_schedule_availability(self.patients, docs_copy, self.base_dt)
        self.last_scheduled = scheduled
        for d in scheduled:
            for a in d.get("appointments",[]):
                s=a["start_dt"].strftime("%I:%M %p").lstrip("0")
                e=a["end_dt"].strftime("%I:%M %p").lstrip("0")
                color_tag="emergency" if a["emergency"] else a["priority"]
                self.s_table.insert("", "end", values=(d["name"],a["name"],s,e,a["priority"],"Yes" if a["emergency"] else "No"), tags=(color_tag,))
        if unassigned: messagebox.showwarning("Unassigned","Could not assign: "+", ".join([p["name"] for p in unassigned]))
        plot_gantt(scheduled, self.base_dt)

    def show_gantt(self):
        if not self.last_scheduled: return
        plot_gantt(self.last_scheduled, self.base_dt)

    def export_csv(self):
        if not self.last_scheduled: return
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files","*.csv")])
        if not filename: return
        with open(filename,"w",newline="") as f:
            writer = csv.writer(f)
            writer.writerow(("Doctor","Patient","Start","End","Priority","Emergency"))
            for d in self.last_scheduled:
                for a in d.get("appointments",[]):
                    writer.writerow((d["name"],a["name"],a["start_dt"].strftime("%I:%M %p").lstrip("0"),a["end_dt"].strftime("%I:%M %p").lstrip("0"),a["priority"],"Yes" if a["emergency"] else "No"))
        messagebox.showinfo("Exported","Schedule exported successfully.")

    def show_summary(self):
        if not self.last_scheduled: return
        names=[]; counts=[]; utilization=[]
        for d in self.last_scheduled:
            names.append(d["name"])
            total_mins = sum([a["time"] for a in d.get("appointments",[])])
            counts.append(len(d.get("appointments",[])))
            total_available = (datetime.datetime.combine(self.base_dt.date(),d["available_to"])-datetime.datetime.combine(self.base_dt.date(),d["available_from"])).total_seconds()/60
            utilization.append(total_mins/total_available*100 if total_available>0 else 0)
        fig, ax = plt.subplots(figsize=(8,5))
        ax.bar(names, utilization,color="skyblue")
        for i,v in enumerate(utilization): ax.text(i,v+1,f"{v:.1f}%",ha="center")
        ax.set_ylabel("% Utilization")
        ax.set_title("Doctor Daily Utilization")
        plt.show()

# -------------------- Run App --------------------
if __name__=="__main__":
    root=tk.Tk()
    style=ttk.Style(root)
    if "clam" in style.theme_names(): style.theme_use("clam")
    app=SchedulerAppProject(root)
    root.mainloop()
