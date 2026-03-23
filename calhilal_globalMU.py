from datetime import datetime, timedelta

import pytz
from skyfield import almanac
from skyfield.almanac import find_discrete, sunrise_sunset
from skyfield.api import Topos, load


# 1. Fungsi Pencarian Ijtima' (New Moon)
def cari_ijtima_terdekat(ts, eph, tahun, bulan, hari):
    t_awal = ts.utc(tahun, bulan, hari - 2)
    t_akhir = ts.utc(tahun, bulan, hari + 1)
    t, y = find_discrete(t_awal, t_akhir, almanac.moon_phases(eph))

    try:
        for i in range(len(t)):
            if y[i] == 0:  # 0 mewakili New Moon
                return ts.tt_jd(t.tt[i])
    except TypeError:
        # Jika t skalar
        if y == 0:
            return t
    return None


# 2. Fungsi Hitung Hilal Lokal
def hitung_hilal_custom(tahun, bulan, hari, lintang, bujur, elevasi, nama_lokasi):
    ts = load.timescale()
    eph = load("de421.bsp")
    sun, moon, earth = eph["sun"], eph["moon"], eph["earth"]

    t_ijtima = cari_ijtima_terdekat(ts, eph, tahun, bulan, hari)
    posisi_coords = Topos(
        latitude_degrees=lintang, longitude_degrees=bujur, elevation_m=elevasi
    )
    lokasi = earth + posisi_coords

    # Penentuan Sunset
    t0 = ts.utc(tahun, bulan, hari, 0, 0)
    t1 = ts.utc(tahun, bulan, hari, 23, 59)
    t_sun, is_sun_up = find_discrete(t0, t1, sunrise_sunset(eph, posisi_coords))

    try:
        if len(t_sun) == 0:
            return f"Matahari tidak terbenam di {nama_lokasi}."

        sunset_time = None
        for i, status in enumerate(is_sun_up):
            if status == 0:  # 0 berarti matahari terbenam
                sunset_time = ts.tt_jd(t_sun.tt[i])
                break

        if sunset_time is None:
            sunset_time = ts.tt_jd(t_sun.tt[0])

    except TypeError:
        # Pengecekan eksplisit is not None
        if t_sun is None:
            return f"Matahari tidak terbenam di {nama_lokasi}."
        sunset_time = t_sun

    obs = lokasi.at(sunset_time)
    ast_sun = obs.observe(sun).apparent()
    ast_moon = obs.observe(moon).apparent()

    alt_moon, _, _ = ast_moon.altaz()
    elongation = ast_moon.separation_from(ast_sun)

    # PERBAIKAN DI SINI: Gunakan 'is not None'
    umur = (sunset_time.tt - t_ijtima.tt) * 24 if t_ijtima is not None else 0

    return {
        "lokasi": nama_lokasi,
        "ijtima": t_ijtima,
        "magrib": sunset_time,
        "tinggi": alt_moon.degrees,
        "elongasi": elongation.degrees,
        "umur": umur,
    }


# 3. Fungsi Pencarian Global KHGT (5/8)
def cari_lokasi_optimal_khgt(tahun, bulan, hari):
    ts = load.timescale()
    eph = load("de421.bsp")
    sun, moon, earth = eph["sun"], eph["moon"], eph["earth"]

    # Cutoff 00:00 UTC hari berikutnya
    cutoff_utc_dt = datetime(tahun, bulan, hari, 0, 0, tzinfo=pytz.utc) + timedelta(
        days=1
    )
    t_limit = ts.from_datetime(cutoff_utc_dt)

    best_loc = None
    max_h = -99

    # Scan Global
    for lon in range(180, -181, -20):
        for lat in range(-60, 61, 30):
            pos_coords = Topos(latitude_degrees=lat, longitude_degrees=lon)
            t_search_start = ts.from_datetime(cutoff_utc_dt - timedelta(hours=24))
            t_sun, is_sun_up = find_discrete(
                t_search_start, t_limit, sunrise_sunset(eph, pos_coords)
            )

            try:
                if len(t_sun) > 0:
                    sunset_time = None
                    for i in reversed(range(len(t_sun))):
                        if is_sun_up[i] == 0:
                            sunset_time = ts.tt_jd(t_sun.tt[i])
                            break

                    if sunset_time is None:
                        continue

                    obs = (earth + pos_coords).at(sunset_time)
                    h = obs.observe(moon).apparent().altaz()[0].degrees
                    e = (
                        obs.observe(moon)
                        .apparent()
                        .separation_from(obs.observe(sun).apparent())
                        .degrees
                    )

                    if h > max_h:
                        max_h = h
                        best_loc = {
                            "lat": lat,
                            "lon": lon,
                            "h": h,
                            "e": e,
                            "utc": sunset_time,
                        }
            except TypeError:
                pass

    return best_loc


# # --- Blok Eksekusi Utama ---
# print("--- SISTEM ANALISIS HILAL MULTI-KRITERIA ---")
# try:
#     thn = int(input("Masukkan Tahun (YYYY): "))
#     bln = int(input("Masukkan Bulan (1-12): "))
#     tgl = int(input("Masukkan Tanggal (1-31): "))

#     # 1. Hitung di Sabang (Titik Barat Indonesia)
#     res_lokal = hitung_hilal_custom(thn, bln, tgl, 5.89, 95.32, 50, "Sabang, Aceh")

#     if isinstance(res_lokal, dict):
#         # PERBAIKAN DI SINI: Gunakan 'is not None'
#         ijtima_dt = (
#             res_lokal["ijtima"].utc_datetime()
#             if res_lokal["ijtima"] is not None
#             else None
#         )
#         magrib_dt = res_lokal["magrib"].utc_datetime()

#         print(f"\n[DATA LOKAL: {res_lokal['lokasi']}]")
#         if ijtima_dt is not None:
#             print(f"Ijtima' (UTC) : {ijtima_dt.strftime('%Y-%m-%d %H:%M:%S')}")
#         print(f"Magrib (UTC)  : {magrib_dt.strftime('%H:%M:%S')}")
#         print(f"Umur Bulan    : {res_lokal['umur']:.2f} jam")
#         print(f"Tinggi Hilal  : {res_lokal['tinggi']:.4f}°")
#         print(f"Elongasi      : {res_lokal['elongasi']:.4f}°")
#     else:
#         print(res_lokal)

#     # 2. Cari Titik Optimal Global (KHGT)
#     print("\n[MENCARI TITIK OPTIMAL GLOBAL KHGT...]")
#     opt = cari_lokasi_optimal_khgt(thn, bln, tgl)

#     if opt is not None:
#         opt_utc_dt = opt["utc"].utc_datetime()
#         print(f"Lokasi Terbaik: {opt['lat']}°N, {opt['lon']}°E")
#         print(f"Waktu (UTC)   : {opt_utc_dt.strftime('%H:%M:%S')}")
#         print(f"Tinggi Hilal  : {opt['h']:.4f}°")
#         print(f"Elongasi      : {opt['e']:.4f}°")

#         # 3. Kesimpulan Akhir
#         print("\n--- STATUS VALIDASI ---")
#         if isinstance(res_lokal, dict):
#             print(
#                 f"Wujudul Hilal (>0°)  : {'LOLOS' if res_lokal['tinggi'] > 0 else 'GAGAL'}"
#             )
#             print(
#                 f"MABIMS (3°/6.4°)     : {'LOLOS' if res_lokal['tinggi'] >= 3 and res_lokal['elongasi'] >= 6.4 else 'GAGAL'}"
#             )
#         print(
#             f"KHGT Global (5°/8°)  : {'LOLOS' if opt['h'] >= 5 and opt['e'] >= 8 else 'GAGAL'}"
#         )

# except Exception:
#     import traceback

#     print(f"Terjadi kesalahan detail:\n{traceback.format_exc()}")
