import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import base64
from configparser import ConfigParser

# load config
config = ConfigParser()
config.read('config/config.ini')

# load path
path_image_start = config['path']['path_image_start']

# map
def map(df):
    df_new = df.copy()
    # dummy column for size
    # df_new['dummy_column_for_size'] = 15
    fig = px.scatter_mapbox(df_new,
                            lat='lat',
                            lon='lon',
                            hover_name='sub',
                            hover_data={'category': False, 'name': True, 'lat': False, 'lon': False, 'rating': True, 'review_count': True},
                            # what should be showed -> when clicking on data
                            custom_data={'lat', 'lon', 'rating', 'review_count', 'sub'},
                            color='rating',
                            color_continuous_scale='rdylgn',
                            range_color=[0,100],
                            zoom=7,
                            height=500)
    fig.update_layout(mapbox_style='open-street-map')
    # adapt color leged
    fig.update_layout(coloraxis_colorbar=dict(yanchor="bottom", y=0.01, xanchor="left", x=0.01, len=0.35))
    # side distance
    fig.update_layout(margin={'r': 0, 't': 0, 'l': 0, 'b': 0})
    # change marker size
    fig.update_traces(marker={'size': 20})
    # return figure
    return fig


# kpi numbers filter
def kpi_filter(df):
    df_pandas = pd.read_json(df, orient='split')
    sum_rs = df_pandas.shape[0]
    sum_r = df_pandas['review_count'].sum()
    average_stars = df_pandas['rating'].sum()/sum_rs
    return '{}'.format(sum_rs), '{}'.format(sum_r), '{:.0f}'.format(average_stars)


# kpi selected review subject
def kpi_review_subject(click_data, df_filtered_business, list_slider, df_kpi, df_similarity):
    # function to get 3 similar review subjects
    def get_3_similar_subjects(sub, list_slider, df_similarity):
        # filter out subjects which are to small or to big (slider)
        # but selected subject should not be filtered out -> this happens later
        f_small = int(list_slider[0])
        f_big = int(list_slider[1])
        df_pd_filtered_slider = df_pd_filtered_business[((df_pd_filtered_business['rating'] >= f_small) & (df_pd_filtered_business['rating'] <= f_big)) |
                                                        (df_pd_filtered_business['sub'] == sub)]
        list_filtered_business = df_pd_filtered_slider.loc[:, 'sub'].tolist()
        list_similarity_index = df_similarity.index.tolist()
        # filter out subjects without comments (subjects without comments are not in similarity matrix)
        list_filter = [i for i in list_filtered_business if i in list_similarity_index]
        # check if sub has reviews
        if sub in list_filter:
            df_filter = df_similarity.loc[list_filter, [sub]]
            df_most_similar = df_filter.nlargest(4, sub, keep='first')
            # drop first row (similarity 1, to be investigated review subject)
            df_most_similar.drop(index=df_most_similar.index[0], axis=0, inplace=True)
            df_most_similar = pd.merge(df_most_similar, df_pd_filtered_business, left_index=True, right_on='sub', how='left')
            df_most_similar_final = df_most_similar[['name', 'rating', sub]].rename(columns={sub: "similarity"})
            df_most_similar_final.rating = df_most_similar_final.rating.round()
            df_most_similar_final.similarity = df_most_similar_final.similarity.round(decimals=2)
            return df_most_similar_final
        else:
            return df_pd_filtered_slider[['name', 'rating', 'sub']].iloc[0:0].rename(columns={'sub': "similarity"})

    # function to create figure kpis
    def line_charts(df):
        # create figure with subplots
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        # add data
        fig.add_trace(go.Scatter(x=df['iat'],
                                 y=df['stars_review_cm'],
                                 mode='lines',
                                 line_shape='hv',
                                 name='average_rating',
                                 line={'color': '#00ccff',
                                       'width': 4}),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=df['iat'],
                                 y=df['review_n'],
                                 mode='lines',
                                 line_shape='hv',
                                 name='total_reviews',
                                 line={'color': '#ffcc00',
                                       'width': 4}),
                      secondary_y=True)
        # define layout
        fig.update_layout(font_color='#ffffff',
                          font_size=14,
                          paper_bgcolor='#4e5d6c',
                          plot_bgcolor='#4e5d6c',
                          margin={'t': 20, 'b': 30, 'r': 0},
                          showlegend=False)
        # define axes
        fig.update_yaxes(title_text="Average Rating",
                         color='#00ccff',
                         showline=True,
                         linecolor='#ffffff',
                         gridcolor='#b3f0ff',
                         # spacing grid
                         nticks=4,
                         rangemode='tozero',
                         secondary_y=False)
        fig.update_yaxes(title_text="Total Reviews",
                         color='#ffcc00',
                         showline=True,
                         linecolor='#ffffff',
                         gridcolor='#fff0b3',
                         # spacing grid
                         nticks=4,
                         rangemode='tozero',
                         secondary_y=True)
        fig.update_xaxes(showline=True, linecolor='#ffffff', mirror=True)
        # return
        return fig

    # function to load word cloud
    def load_word_cloud():
        try:
            encoded_image = base64.b64encode(open(path_image, 'rb').read())
        except FileNotFoundError:
            path_error = path_image_start + '_no_word_cloud.png'
            encoded_image = base64.b64encode(open(path_error, 'rb').read())
        return encoded_image

    # get pandas dataframe
    df_pd_filtered_business = pd.read_json(df_filtered_business, orient='split')
    # problem with the programm
    # business_id = clickData_dccstore['points'][0]['customdata'][3]
    # workaround
    # hover name = business_id -> this means -> name has to go as hover text
    sub_click = click_data['points'][0]['hovertext']
    # get sub to sub (needed -> otherwise some parts of ther dashboard will be loaded automatically)
    # .values[0] -> needed to not get an object
    sub = df_pd_filtered_business[df_pd_filtered_business['sub'] == sub_click]['sub'].values[0]
    # get name to sub
    name_subject = df_pd_filtered_business[df_pd_filtered_business['sub'] == sub]['name']
    # get rating to sub
    rating_subject = round(df_pd_filtered_business[df_pd_filtered_business['sub'] == sub]['rating'])
    # get review count
    reviews_subject = df_pd_filtered_business[df_pd_filtered_business['sub'] == sub]['review_count']
    # filter by sub
    df_kpi_f = df_kpi[df_kpi['sub'] == sub]
    # mangrove-dataset is not sorted by date
    if 'iat_original' in df_kpi_f.columns:
        df_kpi_f = df_kpi_f.sort_values(by=['iat_original'])
    # add new column -> number of reviews
    df_kpi_f.insert(loc=3, column='review_n', value=np.arange(1, len(df_kpi_f)+1))
    # add new column -> cum mean of stars_review
    df_kpi_f.insert(loc=4, column='stars_review_cm', value=df_kpi_f.rating.cumsum()/df_kpi_f['review_n'])
    # create figure
    fig = line_charts(df_kpi_f)
    # get the three most similar review subjects
    df_most_similar_final = get_3_similar_subjects(sub, list_slider, df_similarity)
    columns = [{"name": i, "id": i} for i in df_most_similar_final.columns]
    data = df_most_similar_final.to_dict('records')
    # workaround needed -> normal approach does not work
    list_sub = list([i for i in sub if i.isalnum()])
    sub_path = "".join(list_sub)
    path_image = path_image_start + sub_path + '.png'
    encoded_image = load_word_cloud()
    src_image = 'data:image/png;base64,{}'.format(encoded_image.decode())
    return sub, name_subject, rating_subject, reviews_subject, fig, columns, data, src_image
