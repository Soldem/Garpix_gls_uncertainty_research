import json
import os
import random
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


PALLET_SIZE = {'length': 1200, 'width': 800, 'height': 1800}
PALLET_VOLUME = PALLET_SIZE['length'] * PALLET_SIZE['width'] * PALLET_SIZE['height'] / 1_000_000_000


def load_cargoes(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('data', {}).get('cargoes', [])


def normalize_cargoes(cargoes):
    for cargo in cargoes:
        if 'mass' in cargo and cargo['mass'] > 1000:
            cargo['mass'] = cargo['mass'] / 1000
        if 'size' in cargo:
            size = cargo['size']
            for dim in ['length', 'width', 'height']:
                if dim in size and size[dim] < 10:
                    size[dim] = size[dim] * 1000
    return cargoes


def get_cargo_volume(cargo):
    size = cargo.get('size', {})
    return size.get('length', 0) * size.get('width', 0) * size.get('height', 0) / 1_000_000_000


def get_cargo_mass(cargo):
    return cargo.get('mass', 0) * cargo.get('count', 1)


def get_total_volume(cargoes):
    return sum(get_cargo_volume(c) * c.get('count', 1) for c in cargoes)


def get_total_mass(cargoes):
    return sum(get_cargo_mass(c) for c in cargoes)


def method_raw(cargoes):
    return {
        'volume': get_total_volume(cargoes),
        'mass': get_total_mass(cargoes),
        'pallets': max(1, int(get_total_volume(cargoes) / PALLET_VOLUME) + 1),
        'fill_rate': min(100, get_total_volume(cargoes) / 91.63 * 100)
    }


def method_palletization(cargoes):
    pallet_volume = PALLET_VOLUME
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

    total_volume = get_total_volume(cargoes)
    total_mass = get_total_mass(cargoes)

    return {
        'volume': total_volume,
        'mass': total_mass,
        'pallets': len(pallets),
        'fill_rate': min(100, total_volume / 91.63 * 100)
    }


def method_transport_selection(cargoes):
    total_volume = get_total_volume(cargoes)
    total_mass = get_total_mass(cargoes)

    if total_volume > 50 or total_mass > 20000:
        transport = 'special'
        capacity = float('inf')
    elif total_volume > 20 or total_mass > 5000:
        transport = 'truck'
        capacity = 91.63
    elif total_volume > 1.7 or total_mass > 1000:
        transport = 'van'
        capacity = 34.56
    else:
        transport = 'pallet'
        capacity = PALLET_VOLUME

    return {
        'volume': total_volume,
        'mass': total_mass,
        'transport': transport,
        'capacity': capacity,
        'pallets': max(1, int(total_volume / PALLET_VOLUME) + 1),
        'fill_rate': min(100, total_volume / capacity * 100) if capacity != float('inf') else 0
    }


def method_resampling(cargoes, num_iterations=10, delta=0.03):
    best_volume = 0
    best_pallets = float('inf')

    for i in range(num_iterations):
        varied_cargoes = []
        for cargo in cargoes:
            new_cargo = json.loads(json.dumps(cargo))
            size = new_cargo.get('size', {})
            for dim in ['length', 'width', 'height']:
                if dim in size and size[dim] > 0:
                    size[dim] = int(round(size[dim] * random.uniform(1 - delta, 1 + delta)))
            varied_cargoes.append(new_cargo)

        volume = get_total_volume(varied_cargoes)
        pallets = max(1, int(volume / PALLET_VOLUME) + 1)

        if pallets < best_pallets or (pallets == best_pallets and volume > best_volume):
            best_pallets = pallets
            best_volume = volume

    return {
        'volume': best_volume,
        'mass': get_total_mass(cargoes),
        'pallets': best_pallets,
        'fill_rate': min(100, best_volume / 91.63 * 100)
    }


def main():
    print("=" * 70)
    print("СРАВНЕНИЕ МЕТОДОВ ПЕРЕСБОРКИ НА 20 СЛУЧАЙНЫХ ГРУЗАХ")
    print("=" * 70)

    data_dir = 'data'
    all_cargoes = []
    files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    files = [f for f in files if '_massnorm' not in f and '_dimnorm' not in f and '_palletized' not in f]

    for file_name in files[:50]:
        path = os.path.join(data_dir, file_name)
        try:
            cargoes = load_cargoes(path)
            if cargoes:
                cargoes = normalize_cargoes(cargoes)
                all_cargoes.extend(cargoes)
        except:
            pass

    print(f"Всего загружено грузов: {len(all_cargoes)}")

    random.seed(42)
    sample = random.sample(all_cargoes, min(20, len(all_cargoes)))
    print(f"Выбрано грузов для теста: {len(sample)}")

    results = []

    r1 = method_raw(sample)
    results.append({'method': 'Без пересборки', **r1})

    r2 = method_palletization(sample)
    results.append({'method': 'Паллетизация', **r2})

    r3 = method_transport_selection(sample)
    results.append({'method': 'Выбор транспорта', **r3})

    r4 = method_resampling(sample, num_iterations=10, delta=0.03)
    results.append({'method': 'Пересборка (±3%)', **r4})

    df = pd.DataFrame(results)

    print("\n" + "=" * 70)
    print("СРАВНЕНИЕ МЕТОДОВ ПЕРЕСБОРКИ")
    print("=" * 70)
    print(df[['method', 'volume', 'mass', 'pallets', 'fill_rate']].to_string(index=False))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    short_names = ['Без\nпересборки', 'Палле-\nтизация', 'Выбор\nтранспорта', 'Пересборка\n(±3%)']

    axes[0].bar(short_names, df['pallets'], color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c'])
    axes[0].set_title('Количество паллет', fontsize=12)
    axes[0].set_ylabel('Паллет', fontsize=11)
    axes[0].grid(True, linestyle='--', alpha=0.3)
    for bar, val in zip(axes[0].patches, df['pallets']):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                     str(val), ha='center', va='bottom', fontsize=10)

    axes[1].bar(short_names, df['fill_rate'], color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c'])
    axes[1].set_title('fill_rate (в фуре)', fontsize=12)
    axes[1].set_ylabel('fill_rate, %', fontsize=11)
    axes[1].grid(True, linestyle='--', alpha=0.3)
    for bar, val in zip(axes[1].patches, df['fill_rate']):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                     f'{val:.1f}%', ha='center', va='bottom', fontsize=10)

    axes[2].bar(short_names, df['volume'], color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c'])
    axes[2].set_title('Общий объём грузов', fontsize=12)
    axes[2].set_ylabel('Объём, м3', fontsize=11)
    axes[2].grid(True, linestyle='--', alpha=0.3)
    for bar, val in zip(axes[2].patches, df['volume']):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                     f'{val:.1f}', ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    os.makedirs('outputs', exist_ok=True)
    plt.savefig('outputs/resampling_comparison.png', dpi=300)
    plt.show()

    print("\n" + "=" * 70)
    print("УЛУЧШЕНИЯ МЕТОДОВ")
    print("=" * 70)

    base = df[df['method'] == 'Без пересборки'].iloc[0]

    for _, row in df.iterrows():
        if row['method'] == 'Без пересборки':
            continue
        pallet_improve = ((base['pallets'] - row['pallets']) / base['pallets'] * 100) if base['pallets'] > 0 else 0
        fill_improve = row['fill_rate'] - base['fill_rate']
        print(f"{row['method']}:")
        print(f"   Паллет: {base['pallets']} -> {row['pallets']} ({pallet_improve:+.1f}%)")
        print(f"   fill_rate: {base['fill_rate']:.1f}% -> {row['fill_rate']:.1f}% ({fill_improve:+.1f} п.п.)")

    df.to_csv('outputs/resampling_comparison.csv', index=False)
    print("\nРезультаты сохранены: outputs/resampling_comparison.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].bar(short_names, df['pallets'], color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c'])
    axes[0].set_title('Количество паллет', fontsize=14)
    axes[0].set_ylabel('Паллет', fontsize=12)
    axes[0].grid(True, linestyle='--', alpha=0.3)
    for bar, val in zip(axes[0].patches, df['pallets']):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                     str(val), ha='center', va='bottom', fontsize=12)

    axes[1].bar(short_names, df['fill_rate'], color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c'])
    axes[1].set_title('fill_rate (в фуре)', fontsize=14)
    axes[1].set_ylabel('fill_rate, %', fontsize=12)
    axes[1].grid(True, linestyle='--', alpha=0.3)
    for bar, val in zip(axes[1].patches, df['fill_rate']):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                     f'{val:.1f}%', ha='center', va='bottom', fontsize=12)

    plt.tight_layout()
    plt.savefig('outputs/resampling_comparison_final.png', dpi=300)
    plt.show()


if __name__ == '__main__':
    main()