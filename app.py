from dash import Dash, dcc, html, Input, Output, State, callback_context
import plotly.express as px
import pandas as pd
import json

# Загрузка данных
df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv')

# Инициализация приложения
app = Dash(__name__)

# Макет приложения
app.layout = html.Div([
    html.H1("Интерактивная панель с кросс-фильтрацией"),
    
    # Информационная панель о текущих фильтрах
    html.Div([
        html.H4("Текущие фильтры:"),
        html.Div(id='filter_info', style={'marginBottom': '20px', 'padding': '10px', 'border': '1px solid #ddd', 'borderRadius': '5px'})
    ]),
    
    # Кнопка сброса фильтров
    html.Button("Сбросить все фильтры", id='reset_button', style={'marginBottom': '20px'}),
    
    # Элементы управления
    html.Div([
        html.H4("Выберите страны:"),
        dcc.Dropdown(
            id='country_selector',
            options=[{'label': country, 'value': country} for country in df['country'].unique()],
            multi=True,
            value=['Germany', 'United States', 'China'],
            style={'width': '100%'}
        ),
        
        html.H4("Переменная для оси Y:"),
        dcc.RadioItems(
            id='y_axis_selector',
            options=[
                {'label': 'Продолжительность жизни', 'value': 'lifeExp'},
                {'label': 'ВВП на душу населения', 'value': 'gdpPercap'},
                {'label': 'Население', 'value': 'pop'}
            ],
            value='lifeExp',
            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
        ),
        
        html.H4("Выберите год:"),
        dcc.Slider(
            id='year_slider',
            min=df['year'].min(),
            max=df['year'].max(),
            step=5,
            marks={year: str(year) for year in range(df['year'].min(), df['year'].max() + 1, 5)},
            value=df['year'].max()
        )
    ], style={'width': '100%', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '10px', 'marginBottom': '20px'}),
    
    # Графики
    html.Div([
        html.Div([
            html.H3("Динамика показателя во времени"),
            html.P("Нажмите на линию, чтобы отфильтровать по стране"),
            dcc.Graph(id='line_chart')
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            html.H3("ВВП и продолжительность жизни"),
            html.P("Нажмите на точку или выделите область для фильтрации"),
            dcc.Graph(id='bubble_chart')
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ]),
    
    html.Div([
        html.Div([
            html.H3("Топ-15 стран по населению"),
            html.P("Нажмите на столбец для фильтрации по стране"),
            dcc.Graph(id='top15_population')
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            html.H3("Население по континентам"),
            html.P("Нажмите на сектор для фильтрации по континенту"),
            dcc.Graph(id='continent_pie')
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
    ]),
    
    # Хранение состояния фильтров
    dcc.Store(id='filter_state', data={
        'countries': ['Germany', 'United States', 'China'],
        'continent': None,
        'year': df['year'].max(),
        'y_axis': 'lifeExp'
    })
])

# Обновление фильтров при взаимодействии с графиками
@app.callback(
    Output('filter_state', 'data'),
    Output('country_selector', 'value'),
    Output('year_slider', 'value'),
    Input('line_chart', 'clickData'),
    Input('bubble_chart', 'clickData'),
    Input('bubble_chart', 'selectedData'),
    Input('top15_population', 'clickData'),
    Input('continent_pie', 'clickData'),
    Input('country_selector', 'value'),
    Input('year_slider', 'value'),
    Input('reset_button', 'n_clicks'),
    State('filter_state', 'data'),
)
def update_filters(line_click, bubble_click, bubble_select, bar_click, pie_click, 
                   selected_countries, selected_year, reset_clicks, current_filter_state):
    ctx = callback_context
    if not ctx.triggered:
        return current_filter_state, selected_countries, selected_year
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Создаем копию текущего состояния фильтров
    new_filter_state = dict(current_filter_state)
    new_filter_state['y_axis'] = current_filter_state.get('y_axis', 'lifeExp')
    
    # Обработка сброса фильтров
    if trigger_id == 'reset_button':
        default_countries = ['Germany', 'United States', 'China']
        return {
            'countries': default_countries,
            'continent': None,
            'year': df['year'].max(),
            'y_axis': 'lifeExp'
        }, default_countries, df['year'].max()
    
    # Обработка изменений выбора стран и года через UI контролы
    if trigger_id == 'country_selector':
        new_filter_state['countries'] = selected_countries
    
    if trigger_id == 'year_slider':
        new_filter_state['year'] = selected_year
    
    # Обработка клика на линейном графике
    if trigger_id == 'line_chart' and line_click:
        country = line_click['points'][0]['customdata'][0]
        new_filter_state['countries'] = [country]
    
    # Обработка клика на пузырьковой диаграмме
    if trigger_id == 'bubble_chart' and bubble_click:
        country = bubble_click['points'][0]['hovertext']
        # Безопасное извлечение континента, если он есть в customdata
        if 'customdata' in bubble_click['points'][0] and len(bubble_click['points'][0]['customdata']) > 1:
            continent = bubble_click['points'][0]['customdata'][1]
            new_filter_state['continent'] = continent
        new_filter_state['countries'] = [country]
    
    # Обработка выделения области на пузырьковой диаграмме
    if trigger_id == 'bubble_chart' and bubble_select:
        selected_countries = [point['hovertext'] for point in bubble_select['points']]
        if selected_countries:
            new_filter_state['countries'] = selected_countries
    
    # Обработка клика на столбчатой диаграмме топ-15
    if trigger_id == 'top15_population' and bar_click:
        country = bar_click['points'][0]['x']
        new_filter_state['countries'] = [country]
    
    # Обработка клика на круговой диаграмме
    if trigger_id == 'continent_pie' and pie_click:
        continent = pie_click['points'][0]['label']
        new_filter_state['continent'] = continent
        # Обновляем список стран для выбранного континента
        continent_countries = df[df['continent'] == continent]['country'].unique().tolist()
        new_filter_state['countries'] = continent_countries[:10]  # Ограничиваем количеством 10 для производительности
    
    return new_filter_state, new_filter_state['countries'], new_filter_state['year']

# Обновление всех графиков на основе состояния фильтров
@app.callback(
    Output('line_chart', 'figure'),
    Output('bubble_chart', 'figure'),
    Output('top15_population', 'figure'),
    Output('continent_pie', 'figure'),
    Output('filter_info', 'children'),
    Input('filter_state', 'data'),
    Input('y_axis_selector', 'value')
)
def update_graphs(filter_state, y_axis):
    selected_countries = filter_state.get('countries', ['Germany', 'United States', 'China'])
    selected_year = filter_state.get('year', df['year'].max())
    selected_continent = filter_state.get('continent')
    
    # Обновляем состояние y_axis
    filter_state['y_axis'] = y_axis
    
    # Подготовка данных для разных графиков
    # Для линейного графика - все годы для выбранных стран
    line_df = df[df['country'].isin(selected_countries)]
    
    # Для остальных графиков - данные за выбранный год
    selected_year_df = df[df['year'] == selected_year]
    
    # Применяем фильтр по континенту, если выбран
    if selected_continent:
        selected_year_df = selected_year_df[selected_year_df['continent'] == selected_continent]
    
    # Фильтрованные данные для пузырьковой диаграммы
    filtered_df = selected_year_df[selected_year_df['country'].isin(selected_countries)]
    if len(filtered_df) == 0:
        filtered_df = selected_year_df.head(10)  # Если нет данных после фильтрации, показываем первые 10 стран
    
    # Линейный график
    line_fig = px.line(
        line_df,
        x='year',
        y=y_axis,
        color='country',
        title=f'{y_axis} Over Time',
        custom_data=['country', 'continent']  # Добавляем custom_data для доступа при клике
    )
    line_fig.update_layout(clickmode='event+select')
    
    # Пузырьковая диаграмма - исправление ошибки custom_data
    bubble_fig = px.scatter(
        filtered_df,
        x='gdpPercap',
        y='lifeExp',
        size='pop',
        color='continent',
        hover_name='country',
        size_max=60,
        title=f'GDP vs Life Expectancy ({selected_year})',
        custom_data=['country', 'continent']  # Исправлено: передаем колонки вместо списка списков
    )
    bubble_fig.update_layout(clickmode='event+select')
    
    # Топ-15 стран по населению
    top15_df = selected_year_df.nlargest(15, 'pop')
    top15_fig = px.bar(
        top15_df,
        x='country',
        y='pop',
        color='continent',
        title=f'Top 15 Countries by Population ({selected_year})'
    )
    top15_fig.update_layout(clickmode='event')
    
    # Круговая диаграмма по континентам
    continent_df = selected_year_df.groupby('continent')['pop'].sum().reset_index()
    continent_fig = px.pie(
        continent_df,
        names='continent',
        values='pop',
        title=f'Population by Continent ({selected_year})'
    )
    continent_fig.update_layout(clickmode='event')
    
    # Информация о текущих фильтрах
    filter_info = [
        html.P(f"Выбранные страны: {', '.join(selected_countries) if selected_countries else 'Все'}"),
        html.P(f"Выбранный год: {selected_year}"),
        html.P(f"Выбранный континент: {selected_continent if selected_continent else 'Все'}"),
        html.P(f"Показатель на оси Y: {y_axis}")
    ]
    
    return line_fig, bubble_fig, top15_fig, continent_fig, filter_info

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)