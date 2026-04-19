import tkinter as tk
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.collections import LineCollection
import numpy as np
from datetime import datetime
import math
import random

SOLAR_CONSTANT   = 1361.0
UV_FRACTION      = 0.07
OZONE_THICKNESS  = 0.30
ATMOS_EXTINCTION = 0.12

UVI_SCALE_FACTOR = 5.69

def solar_zenith_angle(hour: float, latitude_deg: float = 3.1,
                        day_of_year: int = None) -> float:
    if day_of_year is None:
        day_of_year = datetime.now().timetuple().tm_yday

    delta = 23.45 * math.sin(math.radians((360 / 365) * (day_of_year - 81)))

    H = (hour - 12.0) * 15.0

    phi_r   = math.radians(latitude_deg)
    delta_r = math.radians(delta)
    H_r     = math.radians(H)

    cos_theta = (math.sin(phi_r) * math.sin(delta_r) +
                 math.cos(phi_r) * math.cos(delta_r) * math.cos(H_r))
    cos_theta = max(0.0, min(cos_theta, 1.0))
    return math.degrees(math.acos(cos_theta))


def beer_lambert_uv(zenith_deg: float) -> float:

    if zenith_deg >= 90.0:
        return 0.0

    cos_theta = math.cos(math.radians(zenith_deg))
    m = 1.0 / (cos_theta + 0.50572 * (96.07995 - zenith_deg) ** -1.6364)
    k = ATMOS_EXTINCTION + OZONE_THICKNESS
    I_uv = SOLAR_CONSTANT * UV_FRACTION * cos_theta * math.exp(-k * m)
    return max(0.0, I_uv)


def uv_irradiance_to_index(I_uv: float) -> float:

    return I_uv / UVI_SCALE_FACTOR

def safe_exposure_minutes(uvi: float, skin_type: int = 3) -> float:

    med_table = {1: 100, 2: 200, 3: 300, 4: 450, 5: 600, 6: 800}
    MED = med_table.get(skin_type, 300)
    if uvi < 0.5:
        return float('inf')
    E_eff    = uvi * 25.0          # mW/m²
    safe_sec = MED / (E_eff * 1e-3)
    return safe_sec / 60.0


def simulate_daily_uvi(latitude_deg: float = 3.1,
                        cloud_factor: float = 0.85,
                        resolution_minutes: int = 15) -> tuple:

    doy   = datetime.now().timetuple().tm_yday
    hours = np.arange(0, 24, resolution_minutes / 60.0)
    uvi   = []
    for h in hours:
        theta   = solar_zenith_angle(h, latitude_deg, doy)
        I_uv    = beer_lambert_uv(theta)
        noise   = random.gauss(1.0, 0.04) if I_uv > 0 else 1.0
        uvi_val = uv_irradiance_to_index(I_uv) * cloud_factor * noise
        uvi.append(max(0.0, uvi_val))
    return hours, np.array(uvi)


def uvi_category(uvi: float):
    if uvi < 2:
        return "Low",       "#4CAF50", 0
    elif uvi < 5:
        return "Moderate",  "#FFC107", 1
    elif uvi < 7:
        return "High",      "#FF7043", 2
    elif uvi < 10:
        return "Very High", "#E53935", 3
    else:
        return "Extreme",   "#7B1FA2", 4


PROTECTION_TIPS = {
    0: [("🧴", "Sunscreen optional for most"),
        ("😎", "Sunglasses recommended"),
        ("🌳", "Enjoy outdoors freely")],
    1: [("🧴", "Apply SPF 30+ sunscreen"),
        ("😎", "Wear hat & sunglasses"),
        ("⏱️", "Reapply every 2 hours")],
    2: [("🧴", "Apply SPF 50+ sunscreen"),
        ("👕", "Wear UV-protective clothing"),
        ("🌂", "Seek shade 10 AM – 4 PM"),
        ("😎", "UV-blocking sunglasses")],
    3: [("🧴", "SPF 50+ — reapply often"),
        ("👕", "Cover all exposed skin"),
        ("🏠", "Avoid peak hours 10–4 PM"),
        ("😎", "Wrap-around UV-400 glasses"),
        ("💧", "Stay hydrated outdoors")],
    4: [("🏠", "Avoid direct sun exposure!"),
        ("🧴", "Max SPF if unavoidable"),
        ("👕", "Full-coverage clothing"),
        ("🌂", "Shade is essential"),
        ("😎", "UV-400 sunglasses only")]
}


class UVDashboard:
    BG_DARK  = "#0D1B2A"
    BG_CARD  = "#162840"
    ACCENT   = "#00C9FF"
    TEXT_MAIN= "#E8F4FD"
    TEXT_SUB = "#8AB0CC"
    BORDER   = "#1E3A5F"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("UV Exposure Monitoring Dashboard")
        self.root.configure(bg=self.BG_DARK)
        self.root.geometry("1280x820")
        self.root.resizable(True, True)

        # Simulation parameters
        self.location     = "Malaysia"
        self.latitude     = 6.12
        self.cloud_factor = 0.82
        self.skin_type    = 3

        self.hours, self.uvi_data = simulate_daily_uvi(
            self.latitude, self.cloud_factor)

        now = datetime.now()
        self.current_hour = now.hour + now.minute / 60.0
        self.current_uvi  = float(np.interp(
            self.current_hour, self.hours, self.uvi_data))

        self._build_ui()
        self._schedule_refresh()

    # LAYOUT
    def _build_ui(self):
        self._build_header()
        self._build_body()
        self._build_alert_bar()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg="#091520", height=64)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="UV EXPOSURE MONITORING",
                 font=("Courier New", 18, "bold"),
                 fg=self.ACCENT, bg="#091520").pack(side="left", padx=24, pady=14)

        right = tk.Frame(hdr, bg="#091520")
        right.pack(side="right", padx=24)

        tk.Label(right, text=f" {self.location}",
                 font=("Courier New", 11),
                 fg=self.TEXT_SUB, bg="#091520").pack(anchor="e")

        self.lbl_date = tk.Label(right, text="",
                                 font=("Courier New", 11),
                                 fg=self.TEXT_SUB, bg="#091520")
        self.lbl_date.pack(anchor="e")
        self._update_date()

    def _build_body(self):
        body = tk.Frame(self.root, bg=self.BG_DARK)
        body.pack(fill="both", expand=True, padx=16, pady=8)
        for i, w in enumerate([2, 3, 2, 2]):
            body.columnconfigure(i, weight=w)
        body.rowconfigure(0, weight=1)
        self._build_uv_gauge(body)
        self._build_forecast(body)
        self._build_protection(body)
        self._build_outdoor_time(body)

    def _card(self, parent, col, title) -> tk.Frame:
        outer = tk.Frame(parent, bg=self.BORDER)
        outer.grid(row=0, column=col, sticky="nsew", padx=6, pady=6)
        tk.Label(outer, text=title,
                 font=("Courier New", 13, "bold"),
                 fg=self.ACCENT, bg=self.BORDER).pack(fill="x", padx=2, pady=(6, 0))
        inner = tk.Frame(outer, bg=self.BG_CARD)
        inner.pack(fill="both", expand=True, padx=2, pady=(2, 2))
        return inner

    # Current UV Index_Layout
    def _build_uv_gauge(self, parent):
        card = self._card(parent, 0, "Current UV Index")

        fig, ax = plt.subplots(figsize=(2.6, 3.3), facecolor=self.BG_CARD)
        ax.set_facecolor(self.BG_CARD)
        ax.set_aspect('equal')
        ax.axis('off')

        bands = [(0, 2, "#4CAF50"), (2, 5, "#FFC107"),
                 (5, 7, "#FF7043"), (7, 10, "#E53935"), (10, 13, "#7B1FA2")]
        uvi_max = 13.0
        for lo, hi, color in bands:
            a1 = 180 - (lo / uvi_max) * 180
            a2 = 180 - (hi / uvi_max) * 180
            ax.add_patch(mpatches.Wedge(
                (0.5, 0.15), 0.40, a2, a1, width=0.12,
                color=color, transform=ax.transAxes, zorder=2))
        # Needle
        angle_rad = math.radians(
            180 - (min(self.current_uvi, uvi_max) / uvi_max) * 180)
        cx, cy = 0.5, 0.15
        nx = cx + 0.36 * math.cos(angle_rad)
        ny = cy + 0.36 * math.sin(angle_rad)
        ax.annotate("", xy=(nx, ny), xytext=(cx, cy),
                    xycoords='axes fraction', textcoords='axes fraction',
                    arrowprops=dict(arrowstyle="-|>", color="white",
                                   lw=2.0, mutation_scale=14))
        ax.plot(cx, cy, 'o', color='white', ms=6,
                transform=ax.transAxes, zorder=5)

        cat, col, _ = uvi_category(self.current_uvi)
        ax.text(0.5, 0.60, f"{self.current_uvi:.1f}",
                ha='center', va='center', fontsize=34, fontweight='bold',
                color=col, transform=ax.transAxes)
        ax.text(0.5, 0.48, f"UVI  —  {cat}",
                ha='center', va='center', fontsize=12,
                color=self.TEXT_SUB, transform=ax.transAxes)

        for lbl, x in [("Low", 0.07), ("Mod", 0.27),
                        ("High", 0.50), ("V.Hi", 0.74), ("Ext", 0.93)]:
            ax.text(x, -0.04, lbl, ha='center', fontsize=8,
                    color=self.TEXT_SUB, transform=ax.transAxes)

        safe_min = safe_exposure_minutes(self.current_uvi, self.skin_type)
        safe_str = f"~{int(safe_min)} min" if safe_min != float('inf') else "No limit"

        ax.text(0.5, 0.87, f"Risk Level: {cat.upper()}",
                ha='center', fontsize=11, fontweight='bold',
                color=col, transform=ax.transAxes)
        ax.text(0.5, 0.78, f"Safe exposure: {safe_str}  (skin Ⅲ)",
                ha='center', fontsize=9,
                color=self.TEXT_SUB, transform=ax.transAxes)

        theta = solar_zenith_angle(self.current_hour, self.latitude)
        I_uv  = beer_lambert_uv(theta)
        ax.text(0.5, 0.68, f"θ={theta:.1f}°  I={I_uv:.1f} W/m²",
                ha='center', fontsize=8, color="#5577AA",
                transform=ax.transAxes)

        fig.tight_layout(pad=0.3)
        FigureCanvasTkAgg(fig, master=card).get_tk_widget()\
            .pack(fill="both", expand=True, padx=4, pady=4)
        plt.close(fig)

    #Forecast Whole Day UV Index
    def _build_forecast(self, parent):
        card = self._card(parent, 1, "UV Index Forecast — Today")

        fig, ax = plt.subplots(figsize=(4.6, 3.4), facecolor=self.BG_CARD)
        ax.set_facecolor("#0E1F30")

        pts  = np.array([self.hours, self.uvi_data]).T.reshape(-1, 1, 2)
        segs = np.concatenate([pts[:-1], pts[1:]], axis=1)
        seg_colors = [uvi_category((u1 + u2) / 2)[1]
                      for u1, u2 in zip(self.uvi_data[:-1], self.uvi_data[1:])]
        ax.add_collection(LineCollection(segs, colors=seg_colors,
                                         linewidths=2.5, zorder=4))
        ax.fill_between(self.hours, self.uvi_data, alpha=0.15, color=self.ACCENT)

        for lo, hi, c, lbl in [(0, 2, "#4CAF50", "Low"),
                                (2, 5, "#FFC107", "Moderate"),
                                (5, 7, "#FF7043", "High"),
                                (7, 10, "#E53935", "Very High"),
                                (10, 14, "#7B1FA2", "Extreme")]:
            ax.axhspan(lo, hi, alpha=0.07, color=c, zorder=1)
            ax.text(23.5, (lo + hi) / 2, lbl, va='center',
                    fontsize=6.5, color=c, ha='right', alpha=0.75)

        ax.axvline(self.current_hour, color=self.ACCENT,
                   lw=1.5, ls='--', alpha=0.8, zorder=5)
        ax.scatter([self.current_hour], [self.current_uvi],
                   color=self.ACCENT, s=55, zorder=6)
        ax.text(self.current_hour + 0.25, self.current_uvi + 0.3,
                f"Now\n{self.current_uvi:.1f}",
                fontsize=9, color=self.ACCENT, va='bottom')

        pk = int(np.argmax(self.uvi_data))
        ax.scatter([self.hours[pk]], [self.uvi_data[pk]],
                   color="#FF7043", s=70, marker='*', zorder=7)
        ax.text(self.hours[pk] + 0.2, self.uvi_data[pk] + 0.3,
                f"Peak {self.uvi_data[pk]:.1f}", fontsize=9, color="#FF7043")

        ax.set_xlim(5, 20)
        ax.set_ylim(0, 14)
        ax.set_xticks([6, 8, 10, 12, 14, 16, 18, 20])
        ax.set_xticklabels(
            ["6 AM", "8 AM", "10 AM", "12 PM",
             "2 PM", "4 PM", "6 PM", "8 PM"],
            fontsize=9, color=self.TEXT_SUB)
        ax.set_yticks([0, 2, 5, 7, 10, 13])
        ax.set_yticklabels(["0", "2", "5", "7", "10", "13"],
                           fontsize=9, color=self.TEXT_SUB)
        ax.tick_params(colors=self.TEXT_SUB, length=3)
        ax.spines[:].set_color(self.BORDER)
        ax.set_xlabel("Time of Day", fontsize=10, color=self.TEXT_SUB)
        ax.set_ylabel("UV Index", fontsize=10, color=self.TEXT_SUB)

        theta = solar_zenith_angle(self.current_hour, self.latitude)
        I_uv  = beer_lambert_uv(theta)
        ax.set_title(
            f"Beer-Lambert  |  θ={theta:.1f}°  |  "
            f"I_UV={I_uv:.2f} W/m²  |  Cloud={self.cloud_factor:.0%}",
            fontsize=7, color="#5577AA", pad=4)

        fig.tight_layout(pad=0.5)
        FigureCanvasTkAgg(fig, master=card).get_tk_widget()\
            .pack(fill="both", expand=True, padx=4, pady=4)
        plt.close(fig)

    #Protection
    def _build_protection(self, parent):
        card = self._card(parent, 2, "Protection Tips")
        cat, col, level = uvi_category(self.current_uvi)
        tips = PROTECTION_TIPS.get(level, PROTECTION_TIPS[0])

        # Risk banner (top)
        tk.Label(card, text=f"⚠  {cat.upper()} RISK",
                 font=("Courier New", 13, "bold"),
                 fg=col, bg=self.BG_CARD).pack(pady=(12, 4))
        tk.Frame(card, bg=col, height=2).pack(fill="x", padx=16, pady=(0, 10))

        # Tips
        for icon, tip in tips:
            row = tk.Frame(card, bg=self.BG_CARD)
            row.pack(fill="x", padx=14, pady=5)
            tk.Label(row, text=icon, font=("Segoe UI Emoji", 15),
                     bg=self.BG_CARD, width=3).pack(side="left")
            tk.Label(row, text=tip, font=("Courier New", 11),
                     fg=self.TEXT_MAIN, bg=self.BG_CARD,
                     wraplength=170, justify="left").pack(side="left", padx=8)

        # Safe exposure
        safe_min = safe_exposure_minutes(self.current_uvi, self.skin_type)
        if safe_min != float('inf'):
            safe_str = f"Max safe exposure: ~{int(safe_min)} min"
            clr2     = "#FF7043" if safe_min < 30 else "#FFC107"
        else:
            safe_str = "No significant UV risk"
            clr2     = "#4CAF50"

        tk.Frame(card, bg=self.BORDER, height=1).pack(fill="x", padx=12, pady=12)
        tk.Label(card, text=f"⏱  {safe_str}",
                 font=("Courier New", 11, "bold"),
                 fg=clr2, bg=self.BG_CARD).pack(pady=3)
        tk.Label(card, text=f"Fitzpatrick type {self.skin_type}  |  MED model",
                 font=("Courier New", 9),
                 fg=self.TEXT_SUB, bg=self.BG_CARD).pack(pady=(0, 8))

    #Suggestion Outdoor Time
    def _build_outdoor_time(self, parent):
        card = self._card(parent, 3, "Best Outdoor Time")

        safe_windows = []
        in_win, w_start = False, None
        for h, u in zip(self.hours, self.uvi_data):
            if 5 <= h <= 20:
                if u < 5 and not in_win:
                    in_win, w_start = True, h
                elif u >= 5 and in_win:
                    in_win = False
                    safe_windows.append((w_start, h))
        if in_win:
            safe_windows.append((w_start, 20.0))

        danger = [(h, u) for h, u in zip(self.hours, self.uvi_data)
                  if u >= 8 and 5 <= h <= 20]

        def fmt(h):
            return f"{int(h):02d}:{int((h % 1) * 60):02d}"

        # Safe Windows
        tk.Label(card, text="🟢  Safe Windows  (UVI < 5)",
                 font=("Courier New", 11, "bold"),
                 fg="#4CAF50", bg=self.BG_CARD).pack(pady=(18, 6))

        if safe_windows:
            for s, e in safe_windows:
                tk.Label(card, text=f"{fmt(s)}  –  {fmt(e)}",
                         font=("Courier New", 15, "bold"),
                         fg=self.TEXT_MAIN, bg=self.BG_CARD).pack(pady=4)
        else:
            tk.Label(card, text="No safe window today",
                     font=("Courier New", 12), fg="#E53935",
                     bg=self.BG_CARD).pack(pady=4)

        tk.Frame(card, bg=self.BORDER, height=1).pack(fill="x", padx=12, pady=14)

        #Danger Window
        tk.Label(card, text="🔴  Danger Window  (UVI ≥ 8)",
                 font=("Courier New", 11, "bold"),
                 fg="#E53935", bg=self.BG_CARD).pack(pady=(0, 6))

        if danger:
            tk.Label(card,
                     text=f"{fmt(danger[0][0])}  –  {fmt(danger[-1][0])}",
                     font=("Courier New", 15, "bold"),
                     fg="#FF7043", bg=self.BG_CARD).pack(pady=4)
        else:
            tk.Label(card, text="No danger window today",
                     font=("Courier New", 12), fg="#4CAF50",
                     bg=self.BG_CARD).pack(pady=4)

    #Alter Bar
    def _build_alert_bar(self):
        cat, col, level = uvi_category(self.current_uvi)
        safe_min = safe_exposure_minutes(self.current_uvi, self.skin_type)
        safe_str = str(int(safe_min)) if safe_min != float('inf') else "∞"

        if level >= 3:
            msg = (f"⚠  ALERT: UV is {cat.upper()}!  "
                   f"UVI = {self.current_uvi:.1f}  |  "
                   f"Avoid direct sun!  |  "
                   f"Safe exposure < {safe_str} min")
            bg, fg = "#3B0000", "#FF6B6B"
        elif level == 2:
            msg = (f"ℹ  UV is HIGH  (UVI {self.current_uvi:.1f}).  "
                   f"Wear SPF 50+ and seek shade at midday.")
            bg, fg = "#2A1800", "#FFA04A"
        else:
            msg = (f"✅  UV is {cat}  (UVI {self.current_uvi:.1f}).  "
                   f"Good conditions for outdoor activity.")
            bg, fg = "#0A2200", "#7DDB76"

        bar = tk.Frame(self.root, bg=bg, height=42)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Label(bar, text=msg, font=("Courier New", 12, "bold"),
                 fg=fg, bg=bg).pack(expand=True)

    #Refresh

    def _update_date(self):
        self.lbl_date.config(
            text=datetime.now().strftime("%d  %B  %Y   |   %H:%M"))

    def _schedule_refresh(self):
        self._update_date()
        self.root.after(30_000, self._schedule_refresh)

def print_physics_summary(latitude: float = 6.12, cloud_factor: float = 0.82):
    print("=" * 64)
    print("  UV EXPOSURE DASHBOARD  —  Physics Summary")
    print("=" * 64)
    print(f"  Location latitude  : {latitude}° N  ({'Malaysia'})")
    print(f"  Cloud factor       : {cloud_factor:.0%}")
    print(f"  Solar constant I₀  : {SOLAR_CONSTANT} W/m²")
    print(f"  UV spectrum frac.  : {UV_FRACTION:.0%}")
    print(f"  Ozone thickness    : {OZONE_THICKNESS} (normalised DU)")
    print(f"  Extinction coeff k : {ATMOS_EXTINCTION}")
    print(f"  UVI scale factor   : {UVI_SCALE_FACTOR} W/m² per UVI unit")
    print()
    print("  ── Beer-Lambert Law ─────────────────────────────────────")
    print("  I_UV = I₀ · f_UV · cos(θ) · exp(−k · m)")
    print("  m    = 1 / [cos θ + 0.50572·(96.07995−θ)^−1.6364]")
    print()
    print("  ── UV Index ─────────────────────────────────────────────")
    print(f"  UVI  = I_UV / {UVI_SCALE_FACTOR}")
    print("         (calibrated: clear-sky noon, tropics → UVI ≈ 11)")
    print()
    print("  ── Safe Exposure (MED Model) ────────────────────────────")
    print("  T    = MED / (UVI × 25 × 10⁻³ × 60)   [minutes]")
    print("=" * 64)

    now   = datetime.now()
    h     = now.hour + now.minute / 60.0
    theta = solar_zenith_angle(h, latitude)
    I_uv  = beer_lambert_uv(theta)
    uvi_v = uv_irradiance_to_index(I_uv) * cloud_factor
    cat, _, _ = uvi_category(uvi_v)
    safe  = safe_exposure_minutes(uvi_v, skin_type=3)
    safe_s = f"{int(safe)} min" if safe != float('inf') else "No limit"

    print()
    print(f"  Current time       : {now.strftime('%H:%M')}")
    print(f"  Zenith angle θ     : {theta:.2f}°")
    print(f"  UV irradiance      : {I_uv:.3f} W/m²")
    print(f"  UV Index (sim.)    : {uvi_v:.2f}  [{cat}]")
    print(f"  Safe exposure      : {safe_s}  (skin type Ⅲ)")
    print("=" * 64)

if __name__ == "__main__":
    print_physics_summary()
    root = tk.Tk()
    UVDashboard(root)
    root.mainloop()
