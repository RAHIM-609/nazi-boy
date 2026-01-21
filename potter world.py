import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import Image, ImageTk
import io
import threading
import sys


API_BASE = "https://api.potterdb.com/v1"
PAGE_SIZE = 10


class PotterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Harry Potter Fantasy World Explorer")
        self.geometry("1100x700")
        self.resizable(False, False)

        MainPage(self).pack(fill="both", expand=True)


class MainPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # ---------------- STATE ----------------
        self.category = "characters"
        self.api_cache = {}
        self.image_cache = {}
        self.current_request_id = 0
        self.loading = False

        # ---------------- BACKGROUND ----------------
        self.load_background()

        # Overlay for UI
        self.overlay = tk.Frame(self, bg="#1e1e1e")
        self.overlay.place(relwidth=1, relheight=1)

        # ---------------- TITLE ----------------
        tk.Label(
            self.overlay,
            text="The Wizarding World of Harry Potter",
            font=("Garamond", 32, "bold"),
            fg="#d4af37",
            bg="#1e1e1e"
        ).pack(pady=10)

        tk.Label(
            self.overlay,
            text="Explore movies, books, characters, spells, and potions from the magical universe.",
            font=("Arial", 12),
            fg="white",
            bg="#1e1e1e"
        ).pack()

        # ---------------- SEARCH ----------------
        search_frame = tk.Frame(self.overlay, bg="#1e1e1e")
        search_frame.pack(pady=10)

        self.search_entry = tk.Entry(search_frame, width=40, font=("Arial", 12))
        self.search_entry.pack(side="left", padx=10)

        tk.Button(
            search_frame,
            text="Search",
            font=("Arial", 11, "bold"),
            bg="#6a0dad",
            fg="white",
            command=self.search
        ).pack(side="left")

        # ---------------- CATEGORIES ----------------
        cat_frame = tk.Frame(self.overlay, bg="#1e1e1e")
        cat_frame.pack(pady=10)

        for name, value in {
            "Movies": "movies",
            "Books": "books",
            "Characters": "characters",
            "Spells": "spells",
            "Potions": "potions"
        }.items():
            tk.Button(
                cat_frame,
                text=name,
                width=15,
                command=lambda v=value: self.set_category(v)
            ).pack(side="left", padx=5)

        # ---------------- RESULTS ----------------
        self.canvas = tk.Canvas(self.overlay, bg="#1e1e1e", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.overlay, orient="vertical", command=self.canvas.yview)

        self.result_frame = tk.Frame(self.canvas, bg="#1e1e1e")
        self.result_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.result_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=10)
        self.scrollbar.pack(side="right", fill="y")

    # ---------------- BACKGROUND LOADER ----------------
    def load_background(self):
        try:
            img = Image.open("bg.jpg").resize((1100, 700))
            self.bg_image = ImageTk.PhotoImage(img)

            self.bg_canvas = tk.Canvas(self, highlightthickness=0)
            self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
            self.bg_canvas.create_image(0, 0, image=self.bg_image, anchor="nw")
            self.bg_canvas.lower()
        except Exception as e:
            print("Background image failed:", e)

    # ---------------- CATEGORY SWITCH ----------------
    def set_category(self, category):
        if self.loading:
            return
        self.category = category
        self.search()

    # ---------------- SEARCH (SAFE & GUARDED) ----------------
    def search(self):
        if self.loading:
            return

        self.loading = True
        self.current_request_id += 1
        request_id = self.current_request_id

        query = self.search_entry.get().strip()
        cache_key = (self.category, query)

        for w in self.result_frame.winfo_children():
            w.destroy()

        if cache_key in self.api_cache:
            self.loading = False
            self.render_results(self.api_cache[cache_key])
            return

        threading.Thread(
            target=self.fetch_data,
            args=(cache_key, query, request_id),
            daemon=True
        ).start()

    # ---------------- FETCH DATA (PAGINATED) ----------------
    def fetch_data(self, cache_key, query, request_id):
        url = f"{API_BASE}/{self.category}?page[size]={PAGE_SIZE}&page[number]=1"
        if query:
            url += f"&filter[name_cont]={query}"

        try:
            r = requests.get(url, timeout=8)
            r.raise_for_status()

            if request_id != self.current_request_id:
                return  # discard stale request

            data = r.json()["data"]
            self.api_cache[cache_key] = data

            self.after(0, lambda: self.render_results(data))

        except Exception as e:
            if request_id == self.current_request_id:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.loading = False

    # ---------------- RENDER RESULTS ----------------
    def render_results(self, data):
        if not data:
            messagebox.showinfo("No Results", "No matching results found.")
            return

        for item in data:
            self.create_card(item)

    # ---------------- CARD UI ----------------
    def create_card(self, item):
        attr = item["attributes"]
        title = attr.get("name") or attr.get("title") or "Untitled"

        card = tk.Frame(self.result_frame, bg="#2c2c2c", bd=1, relief="solid")
        card.pack(fill="x", pady=10, padx=10)

        # IMAGE OR TITLE FALLBACK
        img_url = attr.get("image")
        photo = None

        if img_url:
            photo = self.image_cache.get(img_url)
            if not photo:
                try:
                    img = Image.open(io.BytesIO(requests.get(img_url, timeout=5).content))
                    img = img.resize((120, 160))
                    photo = ImageTk.PhotoImage(img)
                    self.image_cache[img_url] = photo
                except:
                    photo = None

        if photo:
            lbl = tk.Label(card, image=photo, bg="#2c2c2c")
            lbl.image = photo
            lbl.pack(side="left", padx=10)
        else:
            tk.Label(
                card,
                text=title,
                font=("Arial", 14, "bold"),
                fg="#d4af37",
                bg="#2c2c2c",
                width=20,
                height=8,
                justify="center"
            ).pack(side="left", padx=10)

        info = tk.Frame(card, bg="#2c2c2c")
        info.pack(side="left", fill="both", expand=True)

        tk.Label(
            info,
            text=title,
            font=("Arial", 16, "bold"),
            fg="#d4af37",
            bg="#2c2c2c"
        ).pack(anchor="w")

        for k, v in attr.items():
            if k not in ["image", "name", "title", "slug"] and v:
                tk.Label(
                    info,
                    text=f"{k.replace('_',' ').title()}: {v}",
                    fg="white",
                    bg="#2c2c2c",
                    wraplength=700,
                    justify="left"
                ).pack(anchor="w")


if __name__ == "__main__":
    PotterApp().mainloop()
