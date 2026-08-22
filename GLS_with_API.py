import requests
import json
import time
import os
import uuid
import urllib3
import pandas as pd
import matplotlib.pyplot as plt
import random
import copy

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


GLS_API_CONFIG = {
    'base_url': 'https://back.glsystem.net/api_inner/v1',
    'username': 'solomasov_dv@mail.ru',
    'password': 'RaNdOm_1243_',
    'project_id': 113223
}


class GLSAPIClient:
    def __init__(self, config):
        self.config = config
        self.token = None
        self._login()

    def _login(self):
        print("Авторизация...")
        try:
            response = requests.post(
                f"{self.config['base_url']}/auth/login/",
                json={
                    'username': self.config['username'],
                    'password': self.config['password']
                },
                headers={'Content-Type': 'application/json'},
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                self.token = response.json().get('access_token')
                print("Токен получен")
                return True
            return False
        except Exception as e:
            print(f"Ошибка: {e}")
            return False

    def _request(self, method, endpoint, data=None, params=None):
        if not self.token:
            return None
        url = f"{self.config['base_url']}/{endpoint}"
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        try:
            response = requests.request(method, url, json=data, params=params,
                                        headers=headers, verify=False, timeout=60)
            if response.status_code in [200, 201]:
                return response.json()
            return None
        except:
            return None

    def get_cargo_spaces(self):
        result = self._request('GET', 'cargo/cargo-space/', params={'page_size': 10})
        return result.get('results', []) if result else []

    def create_calculation(self, project_id, cargo_space_ids, cargo_list):
        payload = {
            'project': project_id,
            'input_data': {
                'cargo_spaces': cargo_space_ids,
                'groups': [{
                    'title': 'Группа 1',
                    'group_id': 1,
                    'sort': 1,
                    'pallet': None,
                    'cargoes': cargo_list
                }],
                'settings': {'userSort': False}
            }
        }
        result = self._request('POST', 'calculation/', data=payload)
        return result.get('id') if result else None

    def get_calculation_result(self, project_id, calculation_id):
        return self._request('GET', f'project/{project_id}/',
                             params={'calculation_id': calculation_id})

    def get_fill_rate(self, project_id, calculation_id):
        for _ in range(12):
            result = self.get_calculation_result(project_id, calculation_id)
            if result:
                status = result.get('calculation_status')
                if status == 'success':
                    break
                elif status in ['error', 'failed']:
                    return None
            time.sleep(5)

        if not result:
            return None

        def find_key(data, target_keys):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in target_keys:
                        return value
                    result = find_key(value, target_keys)
                    if result is not None:
                        return result
            elif isinstance(data, list):
                for item in data:
                    result = find_key(item, target_keys)
                    if result is not None:
                        return result
            return None

        fill_rate = find_key(result, ['filling_space_percent', 'density_percent', 'fill_rate'])
        if fill_rate is not None:
            gp_type = None
            if 'cargo_spaces' in result and result['cargo_spaces']:
                gp_type = result['cargo_spaces'][0].get('type', 'unknown')
            return {'fill_rate': float(fill_rate), 'gp_type': gp_type}
        return None

    def convert_cargo_for_api(self, raw_cargo):
        size = raw_cargo.get('size', {})
        info = raw_cargo.get('info', {})
        return {
            'cargo_id': raw_cargo.get('cargo_id', str(uuid.uuid4())[:8]),
            'title': info.get('title', 'Груз'),
            'article': info.get('article', ''),
            'type': 'box',
            'length': int(size.get('length', 400)),
            'width': int(size.get('width', 300)),
            'height': int(size.get('height', 250)),
            'mass': float(raw_cargo.get('mass', 30)),
            'stacking': raw_cargo.get('stacking', True),
            'turnover': raw_cargo.get('turnover', True),
            'stacking_limit': 0,
            'count': int(raw_cargo.get('count', 1)),
            'sort': int(raw_cargo.get('sort', 1)),
            'margin_length': 0,
            'margin_width': 0
        }


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


def get_total_volume(cargoes):
    total = 0
    for c in cargoes:
        size = c.get('size', {})
        vol = size.get('length', 0) * size.get('width', 0) * size.get('height', 0)
        total += vol * c.get('count', 1)
    return total / 1_000_000_000


def get_total_mass(cargoes):
    total = 0
    for c in cargoes:
        total += c.get('mass', 0) * c.get('count', 1)
    return total


def manual_calculation(cargoes):
    total_volume = get_total_volume(cargoes)
    total_mass = get_total_mass(cargoes)
    pallet_volume = 1.728
    pallets_needed = max(1, int(total_volume / pallet_volume) + 1)

    if total_volume > 50 or total_mass > 20000:
        transport = 'special'
    elif total_volume > 20 or total_mass > 5000:
        transport = 'truck'
    elif total_volume > 1.7 or total_mass > 1000:
        transport = 'van'
    else:
        transport = 'pallet'

    return {
        'volume': total_volume,
        'mass': total_mass,
        'pallets': pallets_needed,
        'transport': transport
    }


def apply_measurement_error(cargo, error_type, error_magnitude=0.05):
    new_cargo = copy.deepcopy(cargo)
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


def simulate_measurement_errors_for_api(client, project_id, gp_id, cargoes, file_name, num_iterations=5):
    error_types = ['none', 'overestimate', 'underestimate', 'random', 'one_dim']
    results = []

    base_cargoes = [client.convert_cargo_for_api(c) for c in cargoes]
    base_calc_id = client.create_calculation(project_id, [gp_id], base_cargoes)
    base_fill_rate = None
    if base_calc_id:
        base_result = client.get_fill_rate(project_id, base_calc_id)
        if base_result:
            base_fill_rate = base_result['fill_rate']

    for error_type in error_types:
        for i in range(num_iterations):
            errored_cargoes = [apply_measurement_error(c, error_type) for c in cargoes]
            api_cargoes = [client.convert_cargo_for_api(c) for c in errored_cargoes]

            calc_id = client.create_calculation(project_id, [gp_id], api_cargoes)
            if calc_id:
                api_result = client.get_fill_rate(project_id, calc_id)
                if api_result:
                    fill_rate = api_result['fill_rate']
                    results.append({
                        'file': file_name,
                        'error_type': error_type,
                        'iteration': i + 1,
                        'fill_rate': fill_rate,
                        'deviation': ((fill_rate - base_fill_rate) / base_fill_rate * 100) if base_fill_rate and base_fill_rate > 0 else 0
                    })
                else:
                    results.append({
                        'file': file_name,
                        'error_type': error_type,
                        'iteration': i + 1,
                        'fill_rate': None,
                        'deviation': None
                    })
            else:
                results.append({
                    'file': file_name,
                    'error_type': error_type,
                    'iteration': i + 1,
                    'fill_rate': None,
                    'deviation': None
                })
            time.sleep(1)

    return pd.DataFrame(results)


def main():
    print("=" * 70)
    print("МАССОВОЕ ТЕСТИРОВАНИЕ API GLS + СИМУЛЯЦИЯ ОШИБОК")
    print("=" * 70)

    client = GLSAPIClient(GLS_API_CONFIG)
    if not client.token:
        print("Нет токена")
        return

    data_dir = 'data'
    all_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    original_files = [f for f in all_files if '_massnorm' not in f and '_dimnorm' not in f and '_palletized' not in f]

    random.seed(42)
    num_files = min(15, len(original_files))
    selected_files = random.sample(original_files, num_files)

    print(f"Всего оригинальных файлов: {len(original_files)}")
    print(f"Выбрано случайных файлов: {len(selected_files)}")
    print(f"Список выбранных файлов:")
    for f in selected_files:
        print(f"   - {f}")

    spaces = client.get_cargo_spaces()
    if not spaces:
        print("Нет ГП")
        return
    gp_id = spaces[0]['id']
    print(f"\nГП: {spaces[0].get('title')} (ID: {gp_id})")

    project_id = GLS_API_CONFIG['project_id']
    results = []
    error_simulation_results = []

    for idx, file_name in enumerate(selected_files):
        print(f"\n{'=' * 70}")
        print(f"[{idx + 1}/{len(selected_files)}] {file_name}")
        print('=' * 70)

        try:
            cargoes = load_cargoes(os.path.join(data_dir, file_name))
            if not cargoes:
                print("Нет грузов")
                continue

            cargoes = normalize_cargoes(cargoes)

            manual = manual_calculation(cargoes)
            print(f"Грузов: {len(cargoes)}")
            print(f"Объём: {manual['volume']:.2f} м3")
            print(f"Масса: {manual['mass']:.0f} кг")
            print(f"Ручной расчёт: {manual['pallets']} паллет, {manual['transport']}")

            print("Отправка в API...")
            api_cargoes = [client.convert_cargo_for_api(c) for c in cargoes]
            calc_id = client.create_calculation(project_id, [gp_id], api_cargoes)

            if calc_id:
                print(f"   Расчёт создан: {calc_id}")
                api_result = client.get_fill_rate(project_id, calc_id)
                if api_result:
                    print(f"   fill_rate: {api_result['fill_rate']:.2f}%, ГП: {api_result['gp_type']}")
                    results.append({
                        'file': file_name,
                        'cargo_count': len(cargoes),
                        'volume_m3': manual['volume'],
                        'mass_kg': manual['mass'],
                        'manual_pallets': manual['pallets'],
                        'manual_transport': manual['transport'],
                        'api_fill_rate': api_result['fill_rate'],
                        'api_gp_type': api_result['gp_type']
                    })
                else:
                    print("   Не удалось получить fill_rate")
            else:
                print("   Не удалось создать расчёт")

            if idx < 3:
                print(f"\nЗапуск симуляции ошибок для {file_name}...")
                error_df = simulate_measurement_errors_for_api(client, project_id, gp_id, cargoes, file_name,
                                                               num_iterations=3)
                error_simulation_results.append(error_df)
                print("   Симуляция ошибок завершена")

        except Exception as e:
            print(f"Ошибка: {e}")

        time.sleep(2)

    print("\n" + "=" * 70)
    print("СВОДНАЯ ТАБЛИЦА")
    print("=" * 70)

    if results:
        df = pd.DataFrame(results)
        print(df.to_string(index=False))

        os.makedirs('outputs', exist_ok=True)
        df.to_csv('outputs/api_batch_results_random.csv', index=False)
        print(f"\nРезультаты сохранены: outputs/api_batch_results_random.csv")

        plt.figure(figsize=(14, 7))
        colors = ['green' if r < 10 else 'orange' if r < 30 else 'red' for r in df['api_fill_rate']]
        plt.bar(df['file'].str.replace('data_for_algoritm_', '').str.replace('.json', ''),
                df['api_fill_rate'], color=colors, alpha=0.8)

        plt.axhline(y=10, color='gray', linestyle='--', alpha=0.7, label='Низкая загрузка (10%)')
        plt.axhline(y=30, color='orange', linestyle='--', alpha=0.7, label='Средняя загрузка (30%)')
        plt.axhline(y=60, color='red', linestyle='--', alpha=0.7, label='Высокая загрузка (60%)')

        plt.xlabel('Файл')
        plt.ylabel('fill_rate, %')
        plt.title(f'fill_rate по данным API GLS ({len(results)} случайных файлов)')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig('outputs/api_batch_fill_rate_random.png', dpi=300)
        plt.show()

        print("\nСТАТИСТИКА:")
        print(f"   Всего файлов: {len(results)}")
        print(f"   Средний fill_rate: {df['api_fill_rate'].mean():.2f}%")
        print(f"   Минимальный: {df['api_fill_rate'].min():.2f}%")
        print(f"   Максимальный: {df['api_fill_rate'].max():.2f}%")
        print(f"   Медиана: {df['api_fill_rate'].median():.2f}%")

    if error_simulation_results:
        error_df = pd.concat(error_simulation_results, ignore_index=True)
        error_df.to_csv('outputs/error_simulation_api_results.csv', index=False)

        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТЫ СИМУЛЯЦИИ ОШИБОК (через API)")
        print("=" * 70)

        summary = error_df.groupby('error_type').agg({
            'fill_rate': ['mean', 'min', 'max'],
            'deviation': ['mean']
        }).round(2)
        print(summary)

        plt.figure(figsize=(12, 6))
        error_types = ['none', 'overestimate', 'underestimate', 'random', 'one_dim']
        colors_map = {'none': 'green', 'overestimate': 'orange', 'underestimate': 'orange',
                      'random': 'blue', 'one_dim': 'red'}

        for error_type in error_types:
            subset = error_df[error_df['error_type'] == error_type]
            if not subset.empty:
                plt.scatter([error_type] * len(subset), subset['fill_rate'],
                            color=colors_map.get(error_type, 'gray'), alpha=0.6,
                            label=error_type if len(subset) > 0 else '')

        plt.xlabel('Тип ошибки')
        plt.ylabel('fill_rate, %')
        plt.title('Влияние ошибок измерения на fill_rate (API)')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
        plt.savefig('outputs/error_simulation_api_plot.png', dpi=300)
        plt.show()

        print("\nРезультаты симуляции ошибок сохранены: outputs/error_simulation_api_results.csv")


if __name__ == '__main__':
    main()