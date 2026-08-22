import json
import os
import csv
import math
import random


TRANSPORT_TYPES = {
    'pallet': {
        'name': 'Европаллета',
        'length': 1200,
        'width': 800,
        'height': 1800,
        'max_mass': 1000,
        'max_volume': 1.728,
        'description': 'Стандартная паллета 1200×800×1800'
    },
    'van': {
        'name': 'Фургон',
        'length': 6000,
        'width': 2400,
        'height': 2400,
        'max_mass': 5000,
        'max_volume': 34.56,
        'description': 'Фургон 6×2.4×2.4 м'
    },
    'truck': {
        'name': 'Фура 13.6 м',
        'length': 13600,
        'width': 2450,
        'height': 2750,
        'max_mass': 20000,
        'max_volume': 91.63,
        'description': 'Фура 13.6×2.45×2.75 м'
    },
    'special': {
        'name': 'Спецтранспорт',
        'length': float('inf'),
        'width': float('inf'),
        'height': float('inf'),
        'max_mass': float('inf'),
        'max_volume': float('inf'),
        'description': 'Специализированный транспорт'
    }
}

PALLET_VOLUME = TRANSPORT_TYPES['pallet']['max_volume']


def normalize_mass(cargo):
    if 'mass' in cargo and cargo['mass'] > 1000:
        cargo['mass'] = cargo['mass'] / 1000
    return cargo


def normalize_dims(cargo):
    if 'size' in cargo:
        size = cargo['size']
        for dim in ['length', 'width', 'height']:
            if dim in size and size[dim] < 10:
                size[dim] = size[dim] * 1000
    return cargo


def get_cargo_volume(cargo):
    size = cargo.get('size', {})
    return size.get('length', 0) * size.get('width', 0) * size.get('height', 0)


def get_cargo_volume_m3(cargo):
    return get_cargo_volume(cargo) / 1_000_000_000


def get_cargo_mass(cargo):
    return cargo.get('mass', 0) * cargo.get('count', 1)


def get_cargo_dimensions(cargo):
    size = cargo.get('size', {})
    return {'length': size.get('length', 0), 'width': size.get('width', 0), 'height': size.get('height', 0)}


def fits_in_transport(cargo, transport):
    dims = get_cargo_dimensions(cargo)
    volume = get_cargo_volume_m3(cargo) * cargo.get('count', 1)
    mass = get_cargo_mass(cargo)
    return (volume <= transport['max_volume'] and mass <= transport['max_mass'] and
            dims['length'] <= transport['length'] and dims['width'] <= transport['width'] and
            dims['height'] <= transport['height'])


def select_transport(cargo):
    for key in ['pallet', 'van', 'truck', 'special']:
        if fits_in_transport(cargo, TRANSPORT_TYPES[key]):
            return key
    return 'special'


def select_transport_for_group(cargoes):
    total_volume = sum(get_cargo_volume_m3(c) * c.get('count', 1) for c in cargoes)
    total_mass = sum(get_cargo_mass(c) for c in cargoes)
    max_length = max(c.get('size', {}).get('length', 0) for c in cargoes)
    max_width = max(c.get('size', {}).get('width', 0) for c in cargoes)
    max_height = max(c.get('size', {}).get('height', 0) for c in cargoes)
    for key in ['pallet', 'van', 'truck', 'special']:
        t = TRANSPORT_TYPES[key]
        if (total_volume <= t['max_volume'] and total_mass <= t['max_mass'] and
            max_length <= t['length'] and max_width <= t['width'] and max_height <= t['height']):
            return key
    return 'special'


def classify_cargoes(cargoes):
    results = []
    stats = {'pallet': {'count': 0, 'volume': 0, 'mass': 0},
             'van': {'count': 0, 'volume': 0, 'mass': 0},
             'truck': {'count': 0, 'volume': 0, 'mass': 0},
             'special': {'count': 0, 'volume': 0, 'mass': 0}}
    for cargo in cargoes:
        transport = select_transport(cargo)
        volume = get_cargo_volume_m3(cargo) * cargo.get('count', 1)
        mass = get_cargo_mass(cargo)
        stats[transport]['count'] += 1
        stats[transport]['volume'] += volume
        stats[transport]['mass'] += mass
        results.append({'cargo': cargo, 'transport': transport,
                        'transport_name': TRANSPORT_TYPES[transport]['name'],
                        'volume': volume, 'mass': mass})
    return results, stats


def palletize(cargoes):
    pallet_volume = TRANSPORT_TYPES['pallet']['max_volume'] * 1_000_000_000
    sorted_cargoes = sorted(cargoes, key=get_cargo_volume, reverse=True)
    pallets = []
    current_pallet = []
    current_volume = 0
    for cargo in sorted_cargoes:
        cargo_volume = get_cargo_volume(cargo) * cargo.get('count', 1)
        if cargo_volume > pallet_volume * 0.8:
            pallets.append([cargo])
            continue
        if current_volume + cargo_volume <= pallet_volume:
            current_pallet.append(cargo)
            current_volume += cargo_volume
        else:
            if current_pallet:
                pallets.append(current_pallet)
            current_pallet = [cargo]
            current_volume = cargo_volume
    if current_pallet:
        pallets.append(current_pallet)
    return pallets


def process_file(input_path):
    print(f"\n{'='*70}\n{os.path.basename(input_path)}\n{'='*70}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    cargoes = data.get('data', {}).get('cargoes', [])
    if not cargoes:
        print("Нет грузов")
        return None
    for cargo in cargoes:
        normalize_mass(cargo)
        normalize_dims(cargo)
    classified, stats = classify_cargoes(cargoes)
    total_volume = sum(c['volume'] for c in classified)
    total_mass = sum(c['mass'] for c in classified)
    total_count = len(cargoes)
    recommended_transport = select_transport_for_group(cargoes)
    print(f"Количество грузов: {total_count}")
    print(f"Общий объём: {total_volume:.2f} м3")
    print(f"Общая масса: {total_mass:.2f} кг")
    print(f"Рекомендуемый транспорт: {TRANSPORT_TYPES[recommended_transport]['name']}")
    print("\nРаспределение по транспорту:")
    for key in ['pallet', 'van', 'truck', 'special']:
        if stats[key]['count'] > 0:
            name = TRANSPORT_TYPES[key]['name']
            print(f"   {name}: {stats[key]['count']} грузов, {stats[key]['volume']:.2f} м3, {stats[key]['mass']:.0f} кг")
    print("\nПримеры грузов по типам:")
    for key in ['pallet', 'van', 'truck', 'special']:
        examples = [c for c in classified if c['transport'] == key]
        if examples:
            name = TRANSPORT_TYPES[key]['name']
            ex = examples[0]
            size = get_cargo_dimensions(ex['cargo'])
            print(f"   {name}: {size['length']}×{size['width']}×{size['height']} мм -> {ex['volume']:.2f} м3, {ex['mass']:.0f} кг")
    return {'file': os.path.basename(input_path), 'cargo_count': total_count,
            'total_volume': total_volume, 'total_mass': total_mass,
            'recommended_transport': recommended_transport, 'stats': stats}


def main():
    data_dir = 'data'
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    original_files = [f for f in json_files if '_massnorm' not in f and '_dimnorm' not in f and '_palletized' not in f]
    original_files.sort()
    print(f"Найдено оригинальных файлов: {len(original_files)}")
    random.seed(42)
    selected_files = random.sample(original_files, min(15, len(original_files)))
    results = []
    for f in selected_files:
        path = os.path.join(data_dir, f)
        result = process_file(path)
        if result:
            results.append(result)
    print("\n" + "="*90)
    print("СВОДНАЯ ТАБЛИЦА ПО ВСЕМ ФАЙЛАМ")
    print("="*90)
    print(f"{'Файл':<35} | {'Грузов':<8} | {'Объём':<10} | {'Масса':<12} | {'Транспорт':<15}")
    print("-"*95)
    total_cargo = total_volume = total_mass = 0
    for r in results:
        total_cargo += r['cargo_count']
        total_volume += r['total_volume']
        total_mass += r['total_mass']
        transport_name = TRANSPORT_TYPES[r['recommended_transport']]['name']
        print(f"{r['file']:<35} | {r['cargo_count']:<8} | {r['total_volume']:.2f} м3 | {r['total_mass']:.2f} кг | {transport_name:<15}")
    print("-"*95)
    print(f"{'ИТОГО':<35} | {total_cargo:<8} | {total_volume:.2f} м3 | {total_mass:.2f} кг")
    os.makedirs('outputs', exist_ok=True)
    with open('outputs/transport_classification.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Файл', 'Грузов', 'Объём (м3)', 'Масса (кг)', 'Рекомендуемый транспорт',
                         'Паллет (шт)', 'Паллет (м3)', 'Фургон (шт)', 'Фургон (м3)',
                         'Фура (шт)', 'Фура (м3)', 'Спец (шт)', 'Спец (м3)'])
        for r in results:
            writer.writerow([
                r['file'], r['cargo_count'], round(r['total_volume'], 2), round(r['total_mass'], 2),
                TRANSPORT_TYPES[r['recommended_transport']]['name'],
                r['stats']['pallet']['count'], round(r['stats']['pallet']['volume'], 2),
                r['stats']['van']['count'], round(r['stats']['van']['volume'], 2),
                r['stats']['truck']['count'], round(r['stats']['truck']['volume'], 2),
                r['stats']['special']['count'], round(r['stats']['special']['volume'], 2)
            ])
    print("\nРезультаты сохранены: outputs/transport_classification.csv")


if __name__ == '__main__':
    main()