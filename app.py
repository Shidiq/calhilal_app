from flask import Flask, render_template, request, jsonify
from calhilal_globalMU import hitung_hilal_custom, cari_lokasi_optimal_khgt
import traceback

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/calculate", methods=["POST"])
def calculate():
    try:
        data = request.json
        date_str = data.get("date") # YYYY-MM-DD
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
        elev = float(data.get("elev"))
        loc_name = data.get("loc_name", "Observasi")
        
        tahun, bulan, hari = map(int, date_str.split("-"))
        
        # Hitung lokal
        res_lokal = hitung_hilal_custom(tahun, bulan, hari, lat, lon, elev, loc_name)
        
        if isinstance(res_lokal, str):
            # Error string message from the custom logic
            return jsonify({"status": "error", "message": res_lokal})
            
        # Hitung global
        opt = cari_lokasi_optimal_khgt(tahun, bulan, hari)
        
        ijtima_dt = res_lokal.get("ijtima").utc_datetime() if res_lokal.get("ijtima") is not None else None
        magrib_dt = res_lokal.get("magrib").utc_datetime() if res_lokal.get("magrib") is not None else None
        
        response = {
            "status": "success",
            "lokal": {
                "ijtima": ijtima_dt.strftime('%d %b %Y %H:%M:%S') if ijtima_dt else "Not Found",
                "magrib": magrib_dt.strftime('%H:%M:%S') if magrib_dt else "--:--:--",
                "magrib_iso": magrib_dt.strftime('%Y-%m-%dT%H:%M:%SZ') if magrib_dt else None,
                "umur": float(round(res_lokal["umur"], 2)),
                "tinggi": float(round(res_lokal["tinggi"], 4)),
                "elongasi": float(round(res_lokal["elongasi"], 4))
            },
            "global": None,
            "validasi": {
                "wujudul_hilal": bool(res_lokal["tinggi"] > 0),
                "mabims": bool(res_lokal["tinggi"] >= 3 and res_lokal["elongasi"] >= 6.4),
                "khgt": False
            }
        }
        
        if opt is not None:
            opt_utc_dt = opt["utc"].utc_datetime()
            response["global"] = {
                "lat": float(opt["lat"]),
                "lon": float(opt["lon"]),
                "utc": opt_utc_dt.strftime('%H:%M:%S'),
                "tinggi": float(round(opt["h"], 4)),
                "elongasi": float(round(opt["e"], 4))
            }
            response["validasi"]["khgt"] = bool(opt["h"] >= 5 and opt["e"] >= 8)
            
        return jsonify(response)
        
    except Exception as e:
        # Avoid huge tracebacks in UI but keep enough context
        trace = traceback.format_exc()
        # For security and user friendliness, returning a short message on error
        return jsonify({"status": "error", "message": f"Terjadi kesalahan perhitungan: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
