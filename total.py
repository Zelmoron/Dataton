import json
import folium
from folium.plugins import Fullscreen, Search, MeasureControl, BeautifyIcon
from datetime import datetime
import os

geojson_file_path = 'fires.geojson' 
if not os.path.exists(geojson_file_path):
    print(f"Ошибка: Файл '{geojson_file_path}' не найден.")
    exit()
try:
    with open(geojson_file_path, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
except Exception as e:
    print(f"Ошибка при чтении или парсинге файла: {e}")
    exit()

# --- 2. Предобработка свойств и извлечение данных для фильтров ---
unique_years = set()
unique_districts = set()

for feature in geojson_data['features']:
    props = feature['properties']

    # Конвертация IDate и init_date, форматирование площади
    if 'IDate' in props and props['IDate'] is not None:
        try:
            props['readable_IDate'] = datetime.fromtimestamp(int(props['IDate']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        except: props['readable_IDate'] = str(props['IDate'])
    else: props['readable_IDate'] = "N/A"

    if 'area' in props and props['area'] is not None:
        try:
            area_val = float(props['area'])
            props['formatted_area'] = f"{area_val:,.2f} кв.м."
            props['area_numeric'] = area_val # Сохраняем числовое значение для фильтрации
        except:
            props['formatted_area'] = str(props['area'])
            props['area_numeric'] = None
    else:
        props['formatted_area'] = "N/A"
        props['area_numeric'] = None

    if 'init_date' in props and props['init_date']:
        try:
            dt_obj = datetime.fromisoformat(props['init_date'].replace('Z', '+00:00'))
            props['formatted_init_date'] = dt_obj.strftime('%Y-%m-%d %H:%M')
            props['year'] = dt_obj.year # Для фильтра по году
            unique_years.add(dt_obj.year)
        except:
            props['formatted_init_date'] = props['init_date']
            props['year'] = "N/A"
    else:
        props['formatted_init_date'] = "N/A"
        props['year'] = "N/A"

    if 'name_ru' in props and props['name_ru']:
        unique_districts.add(props['name_ru'])
    else:
        props['name_ru'] = "N/A" # Обеспечиваем наличие ключа


sorted_years = sorted(list(filter(lambda x: isinstance(x, int), unique_years)), reverse=True)
sorted_districts = sorted(list(unique_districts))

# Категории площади (примерные границы, можно настроить)
area_categories = {
    "Малые (<10000 кв.м.)": lambda area: area is not None and area < 10000,
    "Средние (10000-100000 кв.м.)": lambda area: area is not None and 10000 <= area < 100000,
    "Крупные (>=100000 кв.м.)": lambda area: area is not None and area >= 100000,
    "Площадь не указана": lambda area: area is None
}

# --- 3. Создание базовой карты ---
if geojson_data['features']:
    first_props = geojson_data['features'][0]['properties']
    try: start_coords = (float(first_props['lat']), float(first_props['lon']))
    except: start_coords = (53.5, 109.0)
else: start_coords = (53.5, 109.0)

m = folium.Map(location=start_coords, zoom_start=7, tiles=None)
folium.TileLayer('OpenStreetMap', name="OpenStreetMap").add_to(m)
folium.TileLayer('CartoDB positron', name="CartoDB Positron").add_to(m)
folium.TileLayer('CartoDB dark_matter', name="CartoDB Dark").add_to(m)
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Esri Satellite', overlay=False, control=True
).add_to(m)

# --- 4. Определение стилей и всплывающих окон (как раньше) ---
popup_fields = ['Id', 'name_ru', 'formatted_init_date', 'formatted_area', 'year', 'lat', 'lon']
popup_aliases = ['ID:', 'Район:', 'Дата начала:', 'Площадь:', 'Год:', 'Широта:', 'Долгота:']
tooltip_fields = ['Id', 'name_ru', 'year']
tooltip_aliases = ['ID:', 'Район:', 'Год:']

def style_function_generic(feature, color='#FF3300', border_color='#A52A2A', weight=1.5, opacity=0.6):
    return {'fillColor': color, 'color': border_color, 'weight': weight, 'fillOpacity': opacity}

def highlight_function_generic(feature):
    return {'fillColor': '#FF6600', 'color': '#A52A2A', 'weight': 3, 'fillOpacity': 0.8}

common_tooltip = folium.features.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, sticky=True)
common_popup = folium.features.GeoJsonPopup(fields=popup_fields, aliases=popup_aliases, localize=True, style="width:300px;")


# --- 5. Создание слоев для фильтров ---

# Слой "Все пожары" (по умолчанию включен)
all_fires_layer_for_search = folium.GeoJson(
    geojson_data,
    name='Все пожары (для поиска и общего вида)',
    style_function=lambda x: style_function_generic(x, color='#e31a1c', border_color='#bd0026'), # Красный
    highlight_function=highlight_function_generic,
    tooltip=common_tooltip,
    popup=common_popup,
    show=True, # По умолчанию ПОКАЗАН
    embed=False # Важно для плагина Search
).add_to(m)

# Фильтры по Годам
year_group = folium.FeatureGroup(name="Фильтр по Годам (выберите один или несколько)", show=True).add_to(m)
for year in sorted_years:
    year_features = {
        "type": "FeatureCollection", "crs": geojson_data.get("crs"),
        "features": [f for f in geojson_data['features'] if f['properties'].get('year') == year]
    }
    if year_features["features"]:
        folium.GeoJson(
            year_features, name=f"Год: {year}",
            style_function=lambda x, y=year: style_function_generic(x, color=f'#{hash(str(y)+"yr")%0xAAAAAA+0x555555:06x}', weight=1), # Разные цвета для годов
            highlight_function=highlight_function_generic,
            tooltip=common_tooltip, popup=common_popup, show=False # По умолчанию выключены
        ).add_to(year_group)

# Фильтры по Районам
district_group = folium.FeatureGroup(name="Фильтр по Районам", show=True).add_to(m)
for district in sorted_districts:
    district_features = {
        "type": "FeatureCollection", "crs": geojson_data.get("crs"),
        "features": [f for f in geojson_data['features'] if f['properties'].get('name_ru') == district]
    }
    if district_features["features"]:
        folium.GeoJson(
            district_features, name=f"Район: {district}",
            style_function=lambda x, d=district: style_function_generic(x, color=f'#{hash(str(d)+"dist")%0xAAAAAA+0x555555:06x}', weight=1),
            highlight_function=highlight_function_generic,
            tooltip=common_tooltip, popup=common_popup, show=False
        ).add_to(district_group)

# Фильтры по Площади
area_group = folium.FeatureGroup(name="Фильтр по Площади", show=True).add_to(m)
area_colors = ['#fee391', '#fec44f', '#fe9929', '#d95f0e'] # Пример цветов для категорий площади
for i, (category_name, condition) in enumerate(area_categories.items()):
    area_features = {
        "type": "FeatureCollection", "crs": geojson_data.get("crs"),
        "features": [f for f in geojson_data['features'] if condition(f['properties'].get('area_numeric'))]
    }
    if area_features["features"]:
        cat_color = area_colors[i % len(area_colors)]
        folium.GeoJson(
            area_features, name=category_name,
            style_function=lambda x, color=cat_color: style_function_generic(x, color=color, weight=1),
            highlight_function=highlight_function_generic,
            tooltip=common_tooltip, popup=common_popup, show=False
        ).add_to(area_group)


# --- 6. Добавление контролов и плагинов ---
folium.LayerControl(collapsed=False, position='topright').add_to(m)
Fullscreen(position="topleft").add_to(m)
MeasureControl(position="topleft", primary_length_unit='kilometers', primary_area_unit='sqmeters').add_to(m)

# Плагин Search (привязан к слою 'all_fires_layer_for_search')
Search(
    layer=all_fires_layer_for_search,
    search_label='name_ru', # Свойство, отображаемое в результатах поиска по умолчанию
    search_properties=['Id', 'name_ru', 'year'], # Список свойств, по которым идет поиск
    placeholder='Поиск по ID, району, году (в слое "Все пожары")...',
    collapsed=True, # Свернут по умолчанию
    geom_type='Polygon',
    position='bottomleft'
).add_to(m)


output_map_file = 'fires_visualization_filtered.html'
m.save(output_map_file)
print(f"Карта с фильтрами сохранена в файл: {output_map_file}")
print(f"Откройте '{output_map_file}' в вашем веб-браузере.")