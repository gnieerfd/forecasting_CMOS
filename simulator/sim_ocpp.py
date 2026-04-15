import asyncio
import websockets
from ocpp.v16 import call
from ocpp.v16 import ChargePoint as cp

class DummyChargePoint(cp):
    async def send_boot_notification(self):
        # Membuat pesan minta izin ke server
        request = call.BootNotification(
            charge_point_model="BRIN-SmartCharger-v1",
            charge_point_vendor="Gania Tech"
        )
        print("Mencoba konek dan kirim BootNotification ke Server...")
        response = await self.call(request)
        print(f"Jawaban dari Server: {response.status}")

async def main():
    # Konek ke WebSocket server yang udah kamu nyalain di port 9000
    async with websockets.connect(
        'ws://localhost:9000/CS_Serpong_01',
        subprotocols=['ocpp1.6']
    ) as ws:
        mesin = DummyChargePoint('CS_Serpong_01', ws)
        
        # Jalankan mesin di background
        task = asyncio.create_task(mesin.start())
        await asyncio.sleep(1) # Tunggu mesin bernapas sebentar
        
        # Kirim pesan BootNotification
        await mesin.send_boot_notification()
        
        # Biarkan simulasi tetap menyala
        await task

if __name__ == '__main__':
    asyncio.run(main())