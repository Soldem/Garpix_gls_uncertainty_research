import json
import os
import csv


def main():
    input_file = 'data/data_for_algoritm_11834_palletized.json'
    output_file = 'outputs/report_11834_final.csv'
    os.makedirs('outputs', exist_ok=True)
    if not os.path.exists(input_file):
        print(f"Файл не найден: {input_file}")
        return
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    pallets = data.get('pallets', [])
    print("=" * 60)
    print("ОТЧЁТ ПО ПАЛЛЕТИЗАЦИИ")
    print("=" * 60)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Паллета', 'Груз', 'Количество', 'Объём (м3)', 'Масса (кг)'])
        for i, pallet in enumerate(pallets, 1):
            pallet_volume = 0
            pallet_mass = 0
            for cargo in pallet:
                size = cargo.get('size', {})
                vol = size.get('length', 0) * size.get('width', 0) * size.get('height', 0) / 1_000_000_000
                count = cargo.get('count', 1)
                mass = cargo.get('mass', 0)
                pallet_volume += vol * count
                pallet_mass += mass * count
                writer.writerow([i, cargo.get('info', {}).get('title', 'Без названия'),
                                 count, round(vol * count, 4), round(mass * count, 2)])
            print(f"Паллета {i}: {len(pallet)} грузов, объём: {pallet_volume:.2f} м3, масса: {pallet_mass:.2f} кг")
    print(f"\nОтчёт сохранён: {output_file}")


if __name__ == '__main__':
    main()