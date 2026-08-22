import json
import os


PALLET_SIZE = {'length': 1200, 'width': 800, 'height': 1800}


def get_cargo_volume(cargo):
    size = cargo.get('size', {})
    return size.get('length', 0) * size.get('width', 0) * size.get('height', 0)


def palletize(cargoes):
    pallet_volume = PALLET_SIZE['length'] * PALLET_SIZE['width'] * PALLET_SIZE['height']
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


def main():
    input_file = 'data/data_for_algoritm_11834_massnorm_dimnorm.json'
    output_file = 'data/data_for_algoritm_11834_palletized.json'
    if not os.path.exists(input_file):
        print(f"Файл не найден: {input_file}")
        return
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    cargoes = data.get('data', {}).get('cargoes', [])
    total_volume = 0
    for cargo in cargoes:
        total_volume += get_cargo_volume(cargo) * cargo.get('count', 1)
    total_volume_m3 = total_volume / 1_000_000_000
    pallet_volume_m3 = PALLET_SIZE['length'] * PALLET_SIZE['width'] * PALLET_SIZE['height'] / 1_000_000_000
    print(f"Общий объём грузов: {total_volume_m3:.2f} м3")
    print(f"Объём одной паллеты: {pallet_volume_m3:.2f} м3")
    print(f"Теоретическое количество паллет: {total_volume_m3 / pallet_volume_m3:.1f}")
    pallets = palletize(cargoes)
    print(f"Фактическое количество паллет: {len(pallets)}")
    result = {'total_volume_m3': total_volume_m3, 'pallet_volume_m3': pallet_volume_m3,
              'pallet_count': len(pallets), 'pallets': pallets}
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Результат сохранён: {output_file}")


if __name__ == '__main__':
    main()