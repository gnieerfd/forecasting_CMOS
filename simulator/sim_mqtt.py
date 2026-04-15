import time
import json
import random
import paho.mqtt.client as mqtt
from datetime import datetime

broker_address = "localhost"
client = mqtt.Client(client_id="Mesin_Simulator_01")
client.connect(broker_address)

# --- KONFIGURASI REALISTIS ---
INTERVAL_DETIK = 60  # Standar telemetri live: 60 detik (1 menit)
meter_energi_total = 188000.0  # Angka awal meteran (seperti odometer mobil)

print("⚡ Simulator MQTT EV Charger (Mode Realistis) Berjalan...")
print(f"🔋 Spesifikasi: DC Fast Charger ~50 kW")
print(f"⏱️ Mengirim data telemetri setiap {INTERVAL_DETIK} detik...\n")

try:
    while True:
        # 1. Simulasi Kelistrikan Fisika (DC Fast Charger)
        voltage = random.uniform(395.0, 405.0) # Tegangan stabil di kisaran 400 Volt DC
        current = random.uniform(120.0, 126.0) # Arus fluktuatif di 120-126 Ampere
        
        # Power (kW) = (Voltage * Current) / 1000
        power_kw = (voltage * current) / 1000.0
        
        # 2. Perhitungan Energi (kWh)
        # Energi = Power (kW) * Waktu (Jam). 60 detik = 1/60 Jam.
        energi_ditambahkan = power_kw * (INTERVAL_DETIK / 3600.0)
        
        # Argometer meteran terus bertambah
        meter_energi_total += energi_ditambahkan
        
        # 3. Bungkus Data JSON
        dummy_data = {
            "timestamp": datetime.now().isoformat(),
            "voltage": round(voltage, 2),
            "current": round(current, 2),
            "power_kw": round(power_kw, 2),
            "energy_kwh": round(meter_energi_total, 2) # Ini yang dibaca oleh database
        }
        
        # 4. Kirim ke Broker
        client.publish("cs/serpong/energy/live", json.dumps(dummy_data))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Terkirim -> Daya Instan: {power_kw:.2f} kW | Argometer Total: {meter_energi_total:.2f} kWh")
        
        # Jeda sebelum pengiriman berikutnya
        time.sleep(INTERVAL_DETIK)
        
except KeyboardInterrupt:
    client.disconnect()
    print("\nSimulator dimatikan dengan aman.")