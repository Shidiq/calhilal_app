let globalMap = null;
let globalMarker = null;

document.addEventListener('DOMContentLoaded', () => {
    // 1. Live datetime update
    const datetimeDisplay = document.getElementById('current-datetime');
    
    function updateDateTime() {
        const now = new Date();
        const options = { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' };
        const datePart = now.toLocaleDateString('en-GB', options);
        const timePart = now.toISOString().substring(11, 19);
        datetimeDisplay.textContent = `${datePart} ${timePart} UTC`;
    }
    
    updateDateTime();
    setInterval(updateDateTime, 1000);

    // 2. Set default date to today
    const dateInput = document.getElementById('date-input');
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;

    // 3. Form Submission
    const form = document.getElementById('calc-form');
    const recalcBtn = document.getElementById('recalc-btn');
    const errorBanner = document.getElementById('error-banner');
    const errorText = document.getElementById('error-text');

    // UI Elements to update
    const elTinggi = document.getElementById('val-tinggi');
    const elElongasi = document.getElementById('val-elongasi');
    const elUmur = document.getElementById('val-umur');
    const elMagrib = document.getElementById('val-magrib');
    
    const uiIjtima = document.getElementById('time-ijtima');
    const uiSunset = document.getElementById('time-sunset');

    const optCoord = document.getElementById('opt-coord');
    const optTinggi = document.getElementById('opt-tinggi');
    const optElongasi = document.getElementById('opt-elongasi');
    const optWaktu = document.getElementById('opt-waktu');
    const optLokasi = document.getElementById('opt-lokasi');

    const latInput = document.getElementById('lat-input');
    const lonInput = document.getElementById('lon-input');
    const presetSelect = document.getElementById('preset-location');

    if (presetSelect) {
        presetSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val) {
                const [lat, lon] = val.split(',');
                latInput.value = lat;
                lonInput.value = lon;
                // Automatically calculate when preset is chosen
                calculateHilalData();
            }
        });
    }

    function updateStatusCircle(id, isSuccess) {
        const item = document.getElementById(id);
        const circle = item.querySelector('.status-circle');
        if (isSuccess) {
            circle.classList.add('success');
        } else {
            circle.classList.remove('success');
        }
    }

    async function getReverseGeocode(lat, lon) {
        try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`, {
                headers: { 'Accept-Language': 'id, en' }
            });
            const data = await res.json();
            if (data && data.address) {
                const parts = [
                    data.address.city || data.address.town || data.address.village || data.address.county,
                    data.address.state || data.address.country
                ].filter(Boolean);
                return parts.join(', ') || data.display_name.split(',').slice(0,2).join(',');
            }
        } catch (e) {
            console.error("Geocoding failed", e);
        }
        return "Lokasi Tidak Diketahui";
    }

    async function calculateHilalData() {
        // 1. Set loading state
        const originalBtnText = recalcBtn.innerHTML;
        recalcBtn.innerHTML = '<i class="ph ph-spinner ph-spin"></i> CALCULATING...';
        recalcBtn.disabled = true;
        errorBanner.classList.add('hidden');

        // Reset UI partially
        elTinggi.textContent = '---';
        elElongasi.textContent = '---';
        elUmur.textContent = '---';
        elMagrib.textContent = '--:--';
        updateStatusCircle('val-wujudul', false);
        updateStatusCircle('val-mabims', false);
        updateStatusCircle('val-khgt', false);

        // 2. Gather data
        const payload = {
            date: dateInput.value,
            lat: document.getElementById('lat-input').value,
            lon: document.getElementById('lon-input').value,
            elev: document.getElementById('elev-input').value
        };

        const locOutput = document.getElementById('output-lokasi');
        locOutput.textContent = "Mencari lokasi...";

        // Trigger Geocoding in parallel (non-blocking)
        getReverseGeocode(payload.lat, payload.lon).then(name => {
            locOutput.textContent = name;
        });

        try {
            // 3. Call API
            const response = await fetch('/api/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.status === 'error') {
                throw new Error(data.message || 'Unknown error occurred.');
            }

            // 4. Update UI with success data
            const local = data.lokal;
            const valid = data.validasi;

            elTinggi.textContent = `${local.tinggi}°`;
            elElongasi.textContent = `${local.elongasi}°`;
            elUmur.textContent = `${local.umur} jam`;
            
            if (local.magrib_iso) {
                const magribDate = new Date(local.magrib_iso);
                elMagrib.textContent = magribDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
            } else {
                elMagrib.textContent = '--:--';
            }
            
            const magribLbl = document.getElementById('val-magrib-lbl');
            if (magribLbl) magribLbl.textContent = `UTC: ${local.magrib}`;

            uiIjtima.textContent = local.ijtima;
            uiSunset.textContent = local.magrib;

            // Updated Status Validation
            updateStatusCircle('val-wujudul', valid.wujudul_hilal);
            updateStatusCircle('val-mabims', valid.mabims);
            updateStatusCircle('val-khgt', valid.khgt);

            // Global Optimal data
            if (data.global) {
                const glob = data.global;
                // Correct negative formatting
                const latStr = `${Math.abs(glob.lat)}°${glob.lat >= 0 ? 'N' : 'S'}`;
                const lonStr = `${Math.abs(glob.lon)}°${glob.lon >= 0 ? 'E' : 'W'}`;
                optCoord.textContent = `${latStr}, ${lonStr}`;
                optTinggi.textContent = `${glob.tinggi}°`;
                optElongasi.textContent = `${glob.elongasi}°`;
                optWaktu.textContent = glob.utc;
                
                if (optLokasi) {
                    optLokasi.textContent = "Mencari lokasi...";
                    getReverseGeocode(glob.lat, glob.lon).then(name => {
                        optLokasi.textContent = name;
                    });
                }

                // Update Map
                const mapContainer = document.getElementById('map');
                if (mapContainer) {
                    if (!globalMap) {
                        globalMap = L.map('map').setView([glob.lat, glob.lon], 3);
                        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                            attribution: '&copy; OpenStreetMap'
                        }).addTo(globalMap);
                        globalMarker = L.marker([glob.lat, glob.lon]).addTo(globalMap);
                    } else {
                        globalMap.setView([glob.lat, glob.lon], 3);
                        globalMarker.setLatLng([glob.lat, glob.lon]);
                    }
                }
            } else {
                optCoord.textContent = 'Not Found';
                optTinggi.textContent = '--';
                optElongasi.textContent = '--';
                optWaktu.textContent = '--:--:--';
                if (optLokasi) optLokasi.textContent = '--';
            }

        } catch (err) {
            console.error(err);
            errorText.textContent = err.message || 'Terjadi kesalahan perhitungan yang tidak diketahui.';
            errorBanner.classList.remove('hidden');
        } finally {
            // Revert loading state
            recalcBtn.innerHTML = originalBtnText;
            recalcBtn.disabled = false;
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await calculateHilalData();
    });

    // Auto trigger calculation on load
    calculateHilalData();
});
