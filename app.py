# import libraries
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input
from dash import dash_table
from dash import dcc
from dash import html
from flask_caching import Cache
from function_folder import *
# ----------------------------------------------------------------------------------------------------


# define variables
# define timeout for memoize function
TIMEOUT = 300
# path_business -> defined in data_import.py
# path_kpi -> defined in data_import.py
# ----------------------------------------------------------------------------------------------------


# create app & cache
app = dash.Dash(external_stylesheets=[dbc.themes.SUPERHERO])
# CACHE_DIR saves file
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache_directory'
})
# ----------------------------------------------------------------------------------------------------


# functions
# memoize data (kpi + business)
@cache.memoize(timeout=TIMEOUT)
def memoize_data():
    return data_import.load_data()


# load data business
def business():
    datasets = memoize_data()
    return pd.read_json(datasets['business'], orient='split')


# load data kpi
def kpi():
    datasets = memoize_data()
    return pd.read_json(datasets['kpi'], orient='split')


# load data similarity
def similarity():
    datasets = memoize_data()
    return pd.read_json(datasets['similarity'], orient='split')


# create dropdown options for categories
def options_category():
    df = business()
    return [{'label': i, 'value': i} for i in df['category']]
# ----------------------------------------------------------------------------------------------------


# css style div
style_div = {'padding': '10px',
             'margin-top': '15px',
             'margin-bottom': '15px',
             'background-color': '#4e5d6c'}

# css style dropdown box
style_box = {'margin-top': '15px'}

# css style dropdown
style_dropdown = {'color': '#212121'}

# css style word cloud
style_wordcloud = {'height': '100%',
                   'width': '100%'}

# css style table
table_alignment = [{'if': {'column_id': 'name'},
                    'textAlign': 'left'}]
table_view = True
table_header = {'backgroundColor': '#2E4053',
                'fontWeight': 'bold'}
table_data = {'backgroundColor': '#4e5d6c'}

# css style slider
style_slider = {'color': '#ffffff',
                'font-size': 'medium'}

# part of layout
controls = dbc.Card(
    [
        html.Div(
            [
                dbc.Label("Select category:"),
                dcc.Dropdown(id='dropdown_category',
                             options=options_category(),
                             # default value
                             value='Food', style=style_dropdown)
            ]
        ),
        html.Div(
            [
                dbc.Label("Select country:"),
                dcc.Dropdown(id='dropdown_country',
                             # options -> output from def
                             # default value
                             value='USA', style=style_dropdown)
            ]
        ),
        html.Div(
            [
                dbc.Label("Select state:"),
                dcc.Dropdown(id='dropdown_state',
                             # options -> output from def
                             # default value
                             value='FL', style=style_dropdown)
            ]
        ),
    ],
    body=True,
    style=style_box
)

# layout
app.layout = dbc.Container(
    [
        dcc.Store(id='store_business'),
        dcc.Store(id='store_subject'),
        # html.P -> Paragraph / Spacing
        html.P(),
        html.H1("Visualizing MANGROVE review subjects"),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(controls, md=2),
                dbc.Col([dbc.Row([dbc.Col(html.Div([html.H5('Total number of review subjects:'),
                                                    html.H6(id='text_filter_subject')], style=style_div), md=4),
                                  dbc.Col(html.Div([html.H5('Total number of reviews:'),
                                                    html.H6(id='text_filter_review')], style=style_div), md=4),
                                  dbc.Col(html.Div([html.H5('Average score in stars:'),
                                                    html.H6(id='text_filter_stars')], style=style_div), md=4)
                                  ]),
                         dbc.Row(dcc.Graph(id='fig_map'), style={'margin-top': '15px',
                                                                 'margin-bottom': '15px'}),
                         dbc.Row([dbc.Col(html.Div([html.H5('Name review subject:'),
                                                    html.H6(id='name_subject')], style=style_div), md=3),
                                  dbc.Col(html.Div([html.H5('Rating review subject:'),
                                                    html.H6(id='rating_subject')], style=style_div), md=3),
                                  dbc.Col(html.Div([html.H5('Number of reviews:'),
                                                    html.H6(id='reviews_subject')], style=style_div), md=3),
                                  dbc.Col(html.Div([html.H5('Review subject id:'),
                                                    html.H6(id='text_subject_id')], style=style_div), md=3)
                                  ]),
                         dbc.Row(dbc.Col(html.Div([html.H5('Cumulative average rating & cumulative sum of all reviews of review subject over time'),
                                                   dcc.Graph(id='fig_subject_kpi')], style=style_div))),
                         dbc.Row([dbc.Col(html.Div([html.H5('Similarity table'),
                                                    html.H6('In this table, the most similar review subjects \
                                                    to the selected review subject are suggested. \
                                                    The similarity is compared only in the active filter.'),
                                                    dash_table.DataTable(id='table',
                                                                         style_cell_conditional=table_alignment,
                                                                         style_as_list_view=table_view,
                                                                         style_header=table_header,
                                                                         style_data=table_data
                                                                         ),
                                                    html.P(),
                                                    html.H5('Rating filter'),
                                                    html.H6('The slider can be used to consider only specific \
                                                    ratings in the similarity table.'),
                                                    html.P(),
                                                    dcc.RangeSlider(id='range_slider',
                                                                    min=0,
                                                                    max=100,
                                                                    marks={0: {'label': '0', 'style': style_slider},
                                                                           20: {'label': '20', 'style': style_slider},
                                                                           40: {'label': '40', 'style': style_slider},
                                                                           60: {'label': '60', 'style': style_slider},
                                                                           80: {'label': '80', 'style': style_slider},
                                                                           100: {'label': '100', 'style': style_slider}},
                                                                    step=10,
                                                                    value=[0,100],
                                                                    dots=True,
                                                                    allowCross=False,
                                                                    updatemode='mouseup',
                                                                    tooltip={'always visible': False,
                                                                             'placement': 'bottom'})], style=style_div), md=6),
                                  dbc.Col(html.Div([html.H5('Word cloud'),
                                                    html.Img(id='image', style=style_wordcloud)], style=style_div), md=6)
                                  ])
                         ], md=10)
             ],
            # filter menu in center -> by uncomment
            #align="center",
        ),
    ],
    fluid=True,
)

# ----------------------------------------------------------------------------------------------------


# callbacks dropdowns
# callback to make dropdown_country dependent
@app.callback(Output('dropdown_country', 'options'),
              [Input('dropdown_category', 'value')])
def cb_dropdown_country(selected_category):
    # create options for country
    df = business()
    filtered_country = df[df['category'] == selected_category]['country'].unique()
    # return options
    return [{'label': i, 'value': i} for i in filtered_country]


# callback to make dropdown_state dependent
@app.callback(Output('dropdown_state', 'options'),
              [Input('dropdown_category', 'value'),
               Input('dropdown_country', 'value')])
def cb_dropdown_state(selected_category, selected_country):
    # create options for state
    df = business()
    filtered_state = df[(df['category'] == selected_category) & (df['country'] == selected_country)]['state'].unique()
    # return options
    return [{'label': i, 'value': i} for i in filtered_state]
# ----------------------------------------------------------------------------------------------------


# callbacks dcc.store
# callback store business
@app.callback(Output('store_business', 'data'),
              [Input('dropdown_category', 'value'),
               Input('dropdown_country', 'value'),
               Input('dropdown_state', 'value')])
def cb_store_business(selected_category, selected_country, selected_state):
    # create filtered df
    df = business()
    filtered_df = df[(df['category'] == selected_category) & (df['country'] == selected_country) & (df['state'] == selected_state)]
    # return filtered df
    return filtered_df.to_json(orient='split')


# callback store subject
@app.callback(Output('store_subject', 'data'),
              [Input('fig_map', 'clickData')])
def cb_store_subject(clickData):
    # return data (json)
    return clickData
# ----------------------------------------------------------------------------------------------------


# callbacks figures
# callback to update map
@app.callback(Output('fig_map', 'figure'),
              [Input('store_business', 'data')])
def cb_fig_map(store_browser_value):
    store_browser_df = pd.read_json(store_browser_value, orient='split')
    # return figure
    return figure.map(store_browser_df)


# callback to update info selected subject
@app.callback(Output('text_subject_id', 'children'),
              Output('name_subject', 'children'),
              Output('rating_subject', 'children'),
              Output('reviews_subject', 'children'),
              Output('fig_subject_kpi', 'figure'),
              Output('table', 'columns'),
              Output('table', 'data'),
              Output('image', 'src'),
              [Input('store_subject', 'data'),
               Input('store_business', 'data'),
               Input('range_slider', 'value')])
def cb_fig_subject(clickData_dccstore, store_browser_value2, list_slider):
    df_kpi = kpi()
    df_similarity = similarity()
    return figure.kpi_review_subject(clickData_dccstore, store_browser_value2, list_slider, df_kpi, df_similarity)


# callback to update info filter (sum rs / sum r / average stars)
@app.callback(Output('text_filter_subject', 'children'),
              Output('text_filter_review', 'children'),
              Output('text_filter_stars', 'children'),
              [Input('store_business', 'data')])
def cb_fig_filter(store_browser_value1):
    return figure.kpi_filter(store_browser_value1)


if __name__ == '__main__':
    app.run_server()
