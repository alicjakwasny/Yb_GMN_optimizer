import asyncio
import json
# Importujemy klasę Frog z pliku frog_client.py
from femtoeasy import frog

async def save_data_samples():
    frog_client = frog()

    # Pętla wykonująca się 5 razy i zapisująca 5 osobnych plików JSON
    for i in range(1, 6):
        print(f'Pobieranie próby {i}/5...')

        data = await frog_client.get_frog_data()

        filename = f'frog_data_{i}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f'Zapisano: {filename}')

        # Krótki odstęp czasowy między pobraniami
        await asyncio.sleep(1)


if __name__ == '__main__':
    asyncio.run(save_data_samples())