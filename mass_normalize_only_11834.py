import json
import os


def normalize_mass(data):
    if 'data' in data and 'cargoes' in data['data']:
        for cargo in data['data']['cargoes']:
            if 'mass' in cargo:
                if cargo['mass'] > 1000:
                    cargo['mass'] = cargo['mass'] / 1000
                    cargo['_mass_normalized'] = True
                else:
                    cargo['_mass_normalized'] = False
    return data


def main():
    input_file = 'data/data_for_algoritm_11834.json'
    output_file = 'data/data_for_algoritm_11834_massnorm.json'
    if not os.path.exists(input_file):
        print(f"Файл не найден: {input_file}")
        return
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    total_mass_before = 0
    for cargo in data.get('data', {}).get('cargoes', []):
        total_mass_before += cargo.get('mass', 0) * cargo.get('count', 1)
    data = normalize_mass(data)
    total_mass_after = 0
    for cargo in data.get('data', {}).get('cargoes', []):
        total_mass_after += cargo.get('mass', 0) * cargo.get('count', 1)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Нормализация масс завершена")
    print(f"   Масса до: {total_mass_before:.2f} кг")
    print(f"   Масса после: {total_mass_after:.2f} кг")
    print(f"   Сохранено: {output_file}")


if __name__ == '__main__':
    main()