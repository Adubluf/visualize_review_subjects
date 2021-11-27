import requests
import pandas as pd
from configparser import ConfigParser
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
import time
import os.path
from datetime import datetime
from math import cos
from math import radians

# load config
config = ConfigParser()
config.read('config/config.ini')

# load path
file_path_rs = config['path']['path_business']
file_path_kpi = config['path']['path_kpi']
file_path_text = config['path']['path_text']


# get reviews from mangrove
def get_mangrove_reviews():
    # define gt_iat
    if os.path.exists(file_path_kpi) == False:
        gt_iat = 1580915880
    else:
        existing_kpi = pd.read_csv(file_path_kpi)
        gt_iat = existing_kpi['iat_original'].max()
    # url definition
    url = 'https://api.mangrove.reviews/reviews?gt_iat=' + str(gt_iat) + '&q=geo:'
    r = requests.get(url)
    json_output = r.json()
    if json_output.get('reviews') != []:
        # normalize pandas output
        reviews_normalize = pd.json_normalize(json_output, record_path="reviews", max_level=2)
        # filter fields
        reviews = reviews_normalize[["payload.sub",
                                     "scheme",
                                     "payload.rating",
                                     "geo.coordinates.lon",
                                     "geo.coordinates.lat",
                                     "payload.iat",
                                     "payload.opinion"]]
        return reviews
    else:
        return json_output


# organize data
def wrangling(df):
    # drop if scheme not geo
    df_wrangling = df.drop(df[df['scheme'] != "geo"].index)
    # drop column scheme
    df_wrangling.drop(['scheme'], axis=1, inplace=True)
    # get review subject name
    name = []
    for i in df_wrangling["payload.sub"]:
        x = i.partition("?q=")[2].partition("&u=")[0]
        if x == '':
            y = i.partition("&q=")[2]
            name.append(y)
        else:
            name.append(x)
    # insert column name
    df_wrangling.insert(1, "name", name, True)
    # rename columns
    df_wrangling = df_wrangling.rename(columns={'payload.sub': 'sub',
                                                'name': 'name',
                                                'payload.rating': 'rating',
                                                'geo.coordinates.lon': 'lon',
                                                'geo.coordinates.lat': 'lat',
                                                'payload.iat': 'iat',
                                                'payload.opinion': 'opinion'})
    # fill nan opinion
    df_wrangling.loc[:, 'opinion'] = df_wrangling.loc[:, 'opinion'].fillna('')
    # add column "review_count"
    df_wrangling['review_count'] = 1
    return df_wrangling


# check language
def language_check_reviews(df):
    # recognize language (en = english text fields and empty text fields)
    # check_language() is not consistent -> does not always return the same result
    def check_language(text):
        try:
            if text == '':
                language = 'en'
            else:
                language = detect(text)
        # when there is a 'LangDetectException'error, term 'other' will be inserted
        except LangDetectException:
            language = 'Other'
        return language
    # use check_language
    df['language'] = df['opinion'].apply(check_language)
    # filter out -> just en -> <= 1000
    df_check = df[df['language'] == 'en']
    # drop column language
    df_check = df_check.drop(['language'], axis=1)
    return df_check


# create csv kpi
def review_kpi(df):
    # function to transform iat into normal time format
    def iat_to_time(time_stamp):
        time_format = datetime.utcfromtimestamp(time_stamp).strftime('%Y-%m-%d %H:%M:%S')
        return time_format
    # create dataframe
    kpi = df[['sub',
              'rating',
              'iat']].rename(columns={'iat': 'iat_original'})
    # use iat_to_time()
    kpi['iat'] = kpi['iat_original'].apply(iat_to_time)
    # export csv
    if os.path.exists(file_path_kpi) == False:
        kpi.to_csv(file_path_kpi, index=False)
    # concat
    else:
        existing_kpi = pd.read_csv(file_path_kpi)
        df_list_kpi = [kpi, existing_kpi]
        kpi_concat = pd.concat(df_list_kpi)
        kpi_concat.to_csv(file_path_kpi, index=False)

# aggregate reviews
def aggregate_reviews(df):
    # drop iat -> not needed for aggregation
    df_drop = df.drop(['iat'], axis=1)
    # group by sub, name, lon & lat
    df_agg = df_drop.groupby(['sub', 'name', 'lon', 'lat'], as_index=False).agg({'opinion': [' '.join],
                                                                                 'review_count': 'sum',
                                                                                 'rating': 'mean'})
    # flattening hierachical index
    df_agg.columns = df_agg.columns.get_level_values(0)
    return df_agg


# create csv text
def review_subject_text(df):
    # create dataframe
    text = df[['sub', 'opinion']]
    # export csv
    if os.path.exists(file_path_text) == False:
        text.to_csv(file_path_text, index=False)
    # aggregate
    else:
        existing_text = pd.read_csv(file_path_text)
        df_list_text = [text, existing_text]
        text_concat = pd.concat(df_list_text)
        text_concat.loc[:, 'opinion'] = text_concat['opinion'].astype(str)
        text_agg = text_concat.groupby(['sub'], as_index=False).agg({'opinion': [' '.join]})
        text_agg.columns = text_agg.columns.get_level_values(0)
        text_agg.to_csv(file_path_text, index=False)


# merge review subjects
def merge_review_subjects(df):
    if os.path.exists(file_path_rs) == True:
        panda_import = pd.read_csv(file_path_rs)
        df_merge = df.merge(panda_import, how='left', on='sub').fillna('empty').rename(columns={'name_x': 'name',
                                                                                                'rating_x': 'rating',
                                                                                                'lon_x': 'lon',
                                                                                                'lat_x': 'lat',
                                                                                                'review_count_x': 'review_count'})
    else:
        df_merge = df
        df_merge.loc[:, ['category', 'city', 'state', 'country']] = 'empty', 'empty', 'empty', 'empty'
    # set new index from 0
    df_merge.reset_index(drop=True, inplace=True)
    return df_merge[['sub', 'name', 'category', 'rating', 'city', 'state', 'country', 'lat', 'lon', 'review_count']]


# get nominatim data
def get_nominatim_data(df):
    def bounding_box(lon, lat):
        # ~ 30 meters in lat
        lat_30 = 1/3710
        grad_lon_1 = 40075 * cos(radians(lat)) / 30 * 1000
        helper_division = grad_lon_1 / 30
        # ~ 30 meters in lon
        lon_30 = 1 / helper_division
        return str(lon-lon_30)+','+str(lat-lat_30)+','+str(lon+lon_30)+','+str(lat+lat_30)
    review_subjects = df
    count = 0
    for index, row in df.iterrows():
        name = row['name']
        lon = round(row['lon'], 7)
        lat = round(row['lat'], 7)
        if row[2] != 'empty':
            print('success (details allready loaded -> nominatim not needed)')
        else:
            try:
                query = {'q': name,
                         'viewbox': bounding_box(lon, lat),
                         'bounded': '1',
                         'format': 'jsonv2',
                         'accept-language': 'en',
                         'addressdetails': '1'}
                r = requests.get('https://nominatim.openstreetmap.org/search', params=query)
                json_output = r.json()
                time.sleep(1.5)
                if len(json_output) == 0:
                    print('no success (nominatim json is empty)')
                    time.sleep(1.5)
                else:
                    df_n = pd.json_normalize(json_output, max_level=2)
                    df_n.loc[:, 'lon'] = pd.to_numeric(df_n['lon'])
                    df_n.loc[:, 'lat'] = pd.to_numeric(df_n['lat'])
                    df_n = df_n.round({'lon': 7, 'lat': 7})
                    if df_n.shape[0] == 0:
                        print('no success (no match for review in nominatim data)')
                        time.sleep(1.5)
                    if df_n.shape[0] == 1:
                        if 'type' in df_n.columns:
                            nom_type = df_n['type']
                            if isinstance(nom_type, str):
                                review_subjects.iat[count, 2] = nom_type
                            else:
                                review_subjects.iat[count, 2] = nom_type.values[0]
                        if 'address.city' in df_n.columns:
                            nom_ac = df_n['address.city']
                            if isinstance(nom_ac, str):
                                review_subjects.iat[count, 4] = nom_ac
                            else:
                                review_subjects.iat[count, 4] = nom_ac.values[0]
                        if 'address.state' in df_n.columns:
                            nom_as = df_n['address.state']
                            if isinstance(nom_as, str):
                                review_subjects.iat[count, 5] = nom_as
                            else:
                                review_subjects.iat[count, 5] = nom_as.values[0]
                        if 'address.country' in df_n.columns:
                            nom_aco = df_n['address.country']
                            if isinstance(nom_aco, str):
                                review_subjects.iat[count, 6] = nom_aco
                            else:
                                review_subjects.iat[count, 6] = nom_aco.values[0]
                        print('success 1 (match for review in nominatim data)')
                        time.sleep(1.5)
                    else:
                        df_n_f = df_n[(df_n['lon'] == lon) & (df_n['lat'] == lat)]
                        if df_n_f.shape[0] == 0:
                            print('no success >1 (no match for review in nominatim data)')
                            time.sleep(1.5)
                        elif df_n_f.shape[0] == 1:
                            if 'type' in df_n_f.columns:
                                nom_type = df_n_f['type']
                                if isinstance(nom_type, str):
                                    review_subjects.iat[count, 2] = nom_type
                                else:
                                    review_subjects.iat[count, 2] = nom_type.values[0]
                            if 'address.city' in df_n_f.columns:
                                nom_ac = df_n_f['address.city']
                                if isinstance(nom_ac, str):
                                    review_subjects.iat[count, 4] = nom_ac
                                else:
                                    review_subjects.iat[count, 4] = nom_ac.values[0]
                            if 'address.state' in df_n_f.columns:
                                nom_as = df_n_f['address.state']
                                if isinstance(nom_as, str):
                                    review_subjects.iat[count, 5] = nom_as
                                else:
                                    review_subjects.iat[count, 5] = nom_as.values[0]
                            if 'address.country' in df_n_f.columns:
                                nom_aco = df_n_f['address.country']
                                if isinstance(nom_aco, str):
                                    review_subjects.iat[count, 6] = nom_aco
                                else:
                                    review_subjects.iat[count, 6] = nom_aco.values[0]
                            print('success >1 (match for review in nominatim data)')
                            time.sleep(1.5)
                        else:
                            print('no success >1 (matching nominatim data can not cannot be clearly identified)')
                            time.sleep(1.5)
            except Exception as e:
                review_subjects.iat[count, 2] = 'error'
                review_subjects.iat[count, 4] = 'error'
                review_subjects.iat[count, 5] = 'error'
                review_subjects.iat[count, 6] = 'error'
                print('no success (error)')
                print(e)
                time.sleep(1.5)
        # adapt counter and additional sleep
        time.sleep(1)
        print('index '+str(count)+' done')
        count += 1
    review_subjects = review_subjects.fillna('not_defined').replace('empty', 'not_defined')
    return review_subjects


# creae rs csv
def final_review_subjects(df):
    if os.path.exists(file_path_rs) == True:
        # concat review subjects
        existing_review_subjects = pd.read_csv(file_path_rs)
        df_list_final = [df, existing_review_subjects]
        review_subject_concat = pd.concat(df_list_final)
        # define types
        review_subject_concat.loc[:, 'sub'] = review_subject_concat['sub'].astype(str)
        review_subject_concat.loc[:, 'name'] = review_subject_concat['name'].astype(str)
        review_subject_concat.loc[:, 'category'] = review_subject_concat['category'].astype(str)
        review_subject_concat.loc[:, 'city'] = review_subject_concat['city'].astype(str)
        review_subject_concat.loc[:, 'state'] = review_subject_concat['state'].astype(str)
        review_subject_concat.loc[:, 'country'] = review_subject_concat['country'].astype(str)
        review_subject_concat.loc[:, 'lat'] = review_subject_concat['lat'].astype(float)
        review_subject_concat.loc[:, 'lon'] = review_subject_concat['lon'].astype(float)
        # create help variable to compute mean
        review_subject_concat['total_rating'] = review_subject_concat['review_count'] * review_subject_concat['rating']
        # group review subjects and aggregate
        review_subjects_final = review_subject_concat.groupby(['sub',
                                                               'name',
                                                               'category',
                                                               'city',
                                                               'state',
                                                               'country',
                                                               'lat',
                                                               'lon'], as_index=False).agg({'review_count': 'sum',
                                                                                            'total_rating': 'sum'})
        # create rating
        review_subjects_final['rating'] = review_subjects_final['total_rating'] / review_subjects_final['review_count']
        # drop column total_rating
        review_subjects_final.drop(['total_rating'], axis=1, inplace=True)
        # flattening hierachical index
        review_subjects_final.columns = review_subjects_final.columns.get_level_values(0)
        review_subjects_final.to_csv(file_path_rs, index=False)
    else:
        df.to_csv(file_path_rs, index=False)


# final function
def get_new_data():
    a = get_mangrove_reviews()
    if isinstance(a, dict):
        print('no new reviews')
    else:
        print(str(a.shape[0]) + ' new review(s)')
        b = wrangling(a)
        c = language_check_reviews(b)
        print(str(c.shape[0]) + ' new english review(s)')
        if c.shape[0] == 0:
            print('no new english review(s)')
        else:
            review_kpi(c)
            d = aggregate_reviews(c)
            review_subject_text(d)
            e = merge_review_subjects(d)
            f = get_nominatim_data(e)
            g = final_review_subjects(f)
