import tkinter as tk
from tkinter import messagebox
from uuid import uuid4
from datetime import datetime
import qrcode
from PIL import Image, ImageTk
import os
import json   # <-- ADDED

# --- FILES (ADDED) ---
DATA_FILE = "parking_data.json"
LOG_FILE = "parking_log.txt"

# --- QR folder ---
if not os.path.exists("qr_codes"):
    os.makedirs("qr_codes")

# ---------------------- PARKING CLASSES ----------------------
class ParkingSlot:
    def __init__(self, slot_id):
        self.slot_id = slot_id
        self.occupied = False
        self.vehicle_info = None

class ParkingLot:
    def __init__(self, capacity=5):
        self.capacity = capacity
        self.slots = [ParkingSlot(i+1) for i in range(capacity)]
        self.waiting_queue = []
        self.log = []
        self.load_data()   # <-- ADDED

    # ---------- FILE HANDLING (ADDED) ----------
    def save_data(self):
        data = {
            "slots": [
                {
                    "slot_id": s.slot_id,
                    "occupied": s.occupied,
                    "vehicle_info": s.vehicle_info
                } for s in self.slots
            ],
            "waiting_queue": self.waiting_queue
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)

            for i, sdata in enumerate(data["slots"]):
                self.slots[i].occupied = sdata["occupied"]
                self.slots[i].vehicle_info = sdata["vehicle_info"]

            self.waiting_queue = data["waiting_queue"]

        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                self.log = f.read().splitlines()

    def save_log(self, text):
        with open(LOG_FILE, "a") as f:
            f.write(text + "\n")

    # ---------- ORIGINAL CODE ----------
    def generate_qr(self, data):
        qr_img = qrcode.make(data)
        filename = f"qr_codes/{data}.png"
        qr_img.save(filename)
        return filename

    def enter_vehicle(self, owner, plate):
        qr_text = str(uuid4())[:8]
        entry_time = datetime.now().strftime("%H:%M:%S")

        free_slot = None
        for slot in self.slots:
            if not slot.occupied:
                free_slot = slot
                break

        qr_file = self.generate_qr(qr_text)

        if free_slot:
            free_slot.occupied = True
            free_slot.vehicle_info = {
                "owner": owner,
                "plate": plate,
                "qr_text": qr_text,
                "qr_file": qr_file,
                "entry": entry_time
            }
            log_text = f"{entry_time}: {owner} ({plate}) parked in Slot {free_slot.slot_id}"
            self.log.append(log_text)
            self.save_log(log_text)   # <-- ADDED
            self.save_data()          # <-- ADDED

            return {"status": "parked", "slot_id": free_slot.slot_id, "qr_text": qr_text, "qr_file": qr_file}

        else:
            self.waiting_queue.append({
                "owner": owner,
                "plate": plate,
                "qr_text": qr_text,
                "qr_file": qr_file,
                "entry": entry_time
            })
            log_text = f"{entry_time}: {owner} ({plate}) waiting (full)"
            self.log.append(log_text)
            self.save_log(log_text)   # <-- ADDED
            self.save_data()          # <-- ADDED

            return {"status": "waiting", "position": len(self.waiting_queue), "qr_text": qr_text, "qr_file": qr_file}

    def exit_vehicle(self, qr_text):
        exit_time = datetime.now().strftime("%H:%M:%S")

        for slot in self.slots:
            if slot.occupied and slot.vehicle_info["qr_text"] == qr_text:
                info = slot.vehicle_info
                slot.occupied = False
                slot.vehicle_info = None
                log_text = f"{exit_time}: {info['owner']} ({info['plate']}) exited Slot {slot.slot_id}"
                self.log.append(log_text)
                self.save_log(log_text)   # <-- ADDED

                if self.waiting_queue:
                    next_car = self.waiting_queue.pop(0)
                    self.enter_vehicle(next_car["owner"], next_car["plate"])

                self.save_data()   # <-- ADDED
                return {"status": "exited", "slot_id": slot.slot_id}

        for i, car in enumerate(self.waiting_queue):
            if car["qr_text"] == qr_text:
                self.waiting_queue.pop(i)
                log_text = f"{exit_time}: {car['owner']} removed from waiting queue"
                self.log.append(log_text)
                self.save_log(log_text)   # <-- ADDED
                self.save_data()          # <-- ADDED
                return {"status": "removed"}

        return {"status": "not_found"}


# ---------------------- GUI (UNCHANGED) ----------------------
class ParkingGUI:
    def __init__(self, root, parking_lot):
        self.root = root
        self.root.title("Smart Parking System (Clean UI)")
        self.root.geometry("900x680")
        self.root.configure(bg="#e9edf3")

        self.lot = parking_lot

        tk.Label(root, text="Smart Car Parking System",
                 font=("Segoe UI", 22, "bold"),
                 bg="#e9edf3", fg="#003f7f").pack(pady=10)

        top_frame = tk.Frame(root, bg="#e9edf3")
        top_frame.pack()

        form = tk.Frame(top_frame, bg="white", bd=1, relief="solid")
        form.grid(row=0, column=0, padx=10)

        tk.Label(form, text="Owner Name:", font=("Segoe UI", 12),
                 bg="white").grid(row=0, column=0, padx=8, pady=5)
        tk.Label(form, text="Car Plate No:", font=("Segoe UI", 12),
                 bg="white").grid(row=1, column=0, padx=8, pady=5)

        self.owner_entry = tk.Entry(form, width=25, font=("Segoe UI", 11))
        self.plate_entry = tk.Entry(form, width=25, font=("Segoe UI", 11))
        self.owner_entry.grid(row=0, column=1, pady=4)
        self.plate_entry.grid(row=1, column=1, pady=4)

        tk.Button(form, text="ENTER VEHICLE", width=20,
                  font=("Segoe UI", 11, "bold"),
                  bg="#0078d4", fg="white",
                  command=self.add_vehicle
                  ).grid(row=2, column=0, columnspan=2, pady=8)

        qr_frame = tk.Frame(top_frame, bg="#e9edf3")
        qr_frame.grid(row=0, column=1, padx=20)

        tk.Label(qr_frame, text="QR Preview",
                 font=("Segoe UI", 13, "bold"),
                 bg="#e9edf3", fg="#003f7f").pack()

        self.qr_label = tk.Label(qr_frame, bg="#e9edf3")
        self.qr_label.pack(pady=5)

        exit_frame = tk.Frame(root, bg="white", bd=1, relief="solid")
        exit_frame.pack(pady=10)

        tk.Label(exit_frame, text="QR Code Text:", font=("Segoe UI", 12),
                 bg="white").grid(row=0, column=0, padx=10, pady=5)
        self.qr_entry = tk.Entry(exit_frame, width=25, font=("Segoe UI", 11))
        self.qr_entry.grid(row=0, column=1)

        tk.Button(exit_frame, text="EXIT VEHICLE", width=20,
                  font=("Segoe UI", 11, "bold"),
                  bg="#d40000", fg="white",
                  command=self.remove_vehicle
                  ).grid(row=1, column=0, columnspan=2, pady=8)

        self.slot_canvas = tk.Canvas(root, width=700, height=120,
                                     bg="#dce3eb", highlightthickness=0)
        self.slot_canvas.pack(pady=8)

        tk.Label(root, text="Waiting Queue",
                 font=("Segoe UI", 13, "bold"),
                 bg="#e9edf3", fg="#003f7f").pack()
        self.wait_list = tk.Listbox(root, width=45, height=4,
                                    font=("Segoe UI", 11))
        self.wait_list.pack(pady=5)

        tk.Label(root, text="System Logs",
                 font=("Segoe UI", 13, "bold"),
                 bg="#e9edf3", fg="#003f7f").pack()
        self.log_box = tk.Listbox(root, width=85, height=9,
                                  font=("Segoe UI", 10))
        self.log_box.pack(pady=8)

        self.update_display()

    # ---------- SAME FUNCTIONS ----------
    def add_vehicle(self):
        owner = self.owner_entry.get()
        plate = self.plate_entry.get()

        if not owner or not plate:
            messagebox.showwarning("Error", "Please enter both fields.")
            return

        res = self.lot.enter_vehicle(owner, plate)

        qr_img = Image.open(res["qr_file"]).resize((130, 130))
        self.tk_qr_img = ImageTk.PhotoImage(qr_img)
        self.qr_label.config(image=self.tk_qr_img)

        self.owner_entry.delete(0, tk.END)
        self.plate_entry.delete(0, tk.END)
        self.update_display()

    def remove_vehicle(self):
        qr_text = self.qr_entry.get()
        res = self.lot.exit_vehicle(qr_text)
        self.qr_entry.delete(0, tk.END)
        self.qr_label.config(image="")
        self.update_display()

    def update_display(self):
        self.slot_canvas.delete("all")
        for i, slot in enumerate(self.lot.slots):
            x = 40 + i * 130
            color = "#6ccb6c" if not slot.occupied else "#ff7878"
            self.slot_canvas.create_rectangle(x, 10, x + 100, 100,
                                              fill=color, outline="#003f7f", width=2)
            text = f"Slot {slot.slot_id}"
            if slot.occupied:
                text += f"\n{slot.vehicle_info['plate']}"
            self.slot_canvas.create_text(x + 50, 55, text=text,
                                         font=("Segoe UI", 10))

        self.wait_list.delete(0, tk.END)
        for i, car in enumerate(self.lot.waiting_queue):
            self.wait_list.insert(tk.END, f"{i+1}. {car['plate']} ({car['qr_text']})")

        self.log_box.delete(0, tk.END)
        for log in self.lot.log[-10:]:
            self.log_box.insert(tk.END, log)


# --- MAIN ---
if __name__ == "__main__":
    root = tk.Tk()
    gui = ParkingGUI(root, ParkingLot(capacity=5))
    root.mainloop()