import json
import os


def normalize_dims(data):
    if 'data' in data and 'cargoes' in data['data']:
        for cargo in data['data']['cargoes']:
            if 'size' in cargo:
                size = cargo['size']
                for dim in ['length', 'width', 'height']:
                    if dim in size:
                        if size[dim] < 10:
                            size[dim] = size[dim] * 1000
                            cargo['_dims_normalized'] = True
                        else:
                            cargo['_dims_normalized'] = False
    return data


def main():
    input_file = 'data/data_for_algoritm_11834_massnorm.json'
    output_file = 'data/data_for_algoritm_11834_massnorm_dimnorm.json'
    if not os.path.exists(input_file):
        print(f"Файл не найден: {input_file}")
        return
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    total_vol_before = 0
    for cargo in data.get('data', {}).get('cargoes', []):
        size = cargo.get('size', {})
        vol = size.get('length', 0) * size.get('width', 0) * size.get('height', 0)
        total_vol_before += vol * cargo.get('count', 1)
    data = normalize_dims(data)
    total_vol_after = 0
    for cargo in data.get('data', {}).get('cargoes', []):
        size = cargo.get('size', {})
        vol = size.get('length', 0) * size.get('width', 0) * size.get('height', 0)
        total_vol_after += vol * cargo.get('count', 1)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Нормализация размеров завершена")
    print(f"   Объём до: {total_vol_before / 1_000_000_000:.2f} м3")
    print(f"   Объём после: {total_vol_after / 1_000_000_000:.2f} м3")
    print(f"   Сохранено: {output_file}")


if __name__ == '__main__':
    main()