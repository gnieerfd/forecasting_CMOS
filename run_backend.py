import time
from datetime import datetime
from services.mqtt_service import CMOSMqttClient
from services.db_service import get_session, EnergyLog

def process_and_save(topic, payload):
    """
    Fungsi callback yang dipanggil otomatis setiap kali ada pesan MQTT masuk.
    Data dari sensor (payload) akan diproses dan disimpan ke database.
    """
    # Mengambil nilai energi dari payload (misalnya dari file sim_mqtt.py)
    # Payload biasanya berisi {'voltage': ..., 'current': ..., 'energy_kwh': ...}
    energi = payload.get("energy_kwh", 0)
    
    # Membuka koneksi/session ke database MySQL (cmos_db)
    session = get_session()
    
    if session:
        try:
            # Membuat entri baru untuk tabel energy_log
            new_entry = EnergyLog(
                Time_Stamp=datetime.now(),
                Energy_Trafo_2=float(energi),
                station_id="CS_Serpong", # ID stasiun agar muncul di filter dashboard
                connector_id=1
            )
            
            # Menambahkan dan menyimpan permanen (commit) ke MySQL
            session.add(new_entry)
            session.commit()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Berhasil simpan ke MySQL: {energi:.2f} kWh (Topik: {topic})")
        
        except Exception as e:
            print(f"❌ Gagal menyimpan data: {e}")
            session.rollback() # Membatalkan jika ada error agar data tidak korup
        
        finally:
            session.close() # Menutup koneksi database

if __name__ == "__main__":
    print("⚡ Memulai CMOS Backend Listener (MQTT -> MySQL)...")
    
    # Inisialisasi klien MQTT dengan konfigurasi broker lokal
    # Menggunakan callback 'process_and_save' untuk menangani pesan masuk
    client = CMOSMqttClient(broker="localhost", on_message_cb=process_and_save)
    
    if client.connect():
        # Berlangganan (Subscribe) ke topik sensor energi
        client.subscribe("cs/serpong/energy/live")
        
        # Menjalankan loop MQTT di background (non-blocking)
        client.loop_start()
        
        print("Sistem sedang mendengarkan data dari mesin...")
        
        try:
            # Menjaga agar script tetap berjalan
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Mematikan sistem dengan rapi saat tombol Ctrl+C ditekan
            client.loop_stop()
            print("\nBackend Listener dihentikan.")
    else:
        print("❌ Gagal terhubung ke MQTT Broker. Pastikan Mosquitto sudah berjalan.")