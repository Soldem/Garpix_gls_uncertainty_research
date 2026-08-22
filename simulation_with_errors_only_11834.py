import json
import random
import pandas as pd
import os


PALLET_SIZE = {'length': 1200, 'width': 800, 'height': 1800}
PALLET_VOLUME = PALLET_SIZE['length'] * PALLET_SIZE['width'] * PALLET_SIZE['height']


def load_cargoes(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('data', {}).get('cargoes', [])


def get_cargo_volume(cargo):
    size = cargo.get('size', {})
    return size.get('length', 0) * size.get('width', 0) * size.get('height', 0)


def get_total_volume(cargoes):
    total = 0
    for c in cargoes:
        total += get_cargo_volume(c) * c.get('count', 1)
    return total


def get_total_mass(cargoes):
    total = 0
    for c in cargoes:
        total += c.get('mass', 0) * c.get('count', 1)
    return total


def apply_measurement_error(cargo, error_type, error_magnitude=0.05):
    new_cargo = json.loads(json.dumps(cargo))
    size = new_cargo.get('size', {})
    if error_type == 'none':
        return new_cargo
    elif error_type == 'overestimate':
        for dim in ['length', 'width', 'height']:
            if dim in size and size[dim] > 0:
                size[dim] = int(round(size[dim] * (1 + error_magnitude)))
    elif error_type == 'underestimate':
        for dim in ['length', 'width', 'height']:
            if dim in size and size[dim] > 0:
                size[dim] = int(round(size[dim] * (1 - error_magnitude)))
    elif error_type == 'random':
        for dim in ['length', 'width', 'height']:
            if dim in size and size[dim] > 0:
                size[dim] = int(round(size[dim] * random.uniform(1 - error_magnitude, 1 + error_magnitude)))
    elif error_type == 'one_dim':
        dims = ['length', 'width', 'height']
        error_dim = random.choice(dims)
        if error_dim in size and size[error_dim] > 0:
            size[error_dim] = int(round(size[error_dim] * 10))
    return new_cargo


def simulate_measurement_errors(cargoes, error_types, num_iterations=10):
    results = []
    base_volume = get_total_volume(cargoes)
    base_mass = get_total_mass(cargoes)
    for error_type in error_types:
        for i in range(num_iterations):
            errored_cargoes = [apply_measurement_error(c, error_type) for c in cargoes]
            new_volume = get_total_volume(errored_cargoes)
            new_mass = get_total_mass(errored_cargoes)
            pallets_needed = new_volume / PALLET_VOLUME if PALLET_VOLUME > 0 else 0
            results.append({
                'error_type': error_type,
                'iteration': i + 1,
                'volume_m3': new_volume / 1_000_000_000,
                'mass_kg': new_mass,
                'volume_deviation': ((new_volume - base_volume) / base_volume * 100) if base_volume > 0 else 0,
                'pallets_needed': pallets_needed,
                'fits_in_pallet': new_volume <= PALLET_VOLUME
            })
    return pd.DataFrame(results)


def main():
    os.makedirs('outputs', exist_ok=True)
    file_path = 'data/data_for_algoritm_12729.json'
    cargoes = load_cargoes(file_path)
    if not cargoes:
        print("Нет грузов")
        return
    print("=" * 70)
    print("СИМУЛЯЦИЯ ВЛИЯНИЯ ОШИБОК ИЗМЕРЕНИЙ")
    print("=" * 70)
    error_types = ['none', 'overestimate', 'underestimate', 'random', 'one_dim']
    results_df = simulate_measurement_errors(cargoes, error_types, num_iterations=10)
    base_volume = get_total_volume(cargoes) / 1_000_000_000
    base_mass = get_total_mass(cargoes)
    pallet_volume_m3 = PALLET_VOLUME / 1_000_000_000
    print(f"\nБазовые параметры (без ошибок):")
    print(f"   Объём: {base_volume:.2f} м3")
    print(f"   Масса: {base_mass:.2f} кг")
    print(f"   Объём паллеты: {pallet_volume_m3:.2f} м3")
    print(f"   Количество паллет: {base_volume / pallet_volume_m3:.1f}")
    print("\n" + "=" * 70)
    print("РЕЗУЛЬТАТЫ СИМУЛЯЦИИ")
    print("=" * 70)
    summary = results_df.groupby('error_type').agg({
        'volume_m3': ['mean', 'std', 'min', 'max'],
        'pallets_needed': ['mean', 'max'],
        'volume_deviation': ['mean']
    }).round(2)
    print(summary)
    print("\n" + "=" * 70)
    print("СРАВНЕНИЕ С БАЗОВЫМ РЕЗУЛЬТАТОМ")
    print("=" * 70)
    for error_type in error_types:
        subset = results_df[results_df['error_type'] == error_type]
        mean_volume = subset['volume_m3'].mean()
        mean_deviation = subset['volume_deviation'].mean()
        max_pallets = subset['pallets_needed'].max()
        if error_type == 'none':
            status = "Без ошибок"
        elif mean_volume > base_volume * 1.1:
            status = "Груз может не поместиться"
        elif mean_volume < base_volume * 0.9:
            status = "Груз занижен (риск недогруза)"
        else:
            status = "В пределах погрешности"
        print(f"{error_type:15} | Объём: {mean_volume:>6.2f} м3 | Отклонение: {mean_deviation:>6.1f}% | Паллет: {max_pallets:>4.1f} | {status}")
    results_df.to_csv('outputs/measurement_error_simulation.csv', index=False)
    print("\nРезультаты сохранены: outputs/measurement_error_simulation.csv")


if __name__ == '__main__':
    main()