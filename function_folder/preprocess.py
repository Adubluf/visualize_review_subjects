from configparser import ConfigParser
import pandas as pd
import numpy as np
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from wordcloud import WordCloud
from unidecode import unidecode
from collections import Counter
import itertools
import os.path
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# load config
config = ConfigParser()
config.read('config/config.ini')

# load path
file_path_last_change = config['path']['path_change']
file_path_kpi = config['path']['path_kpi']
file_path_text = config['path']['path_text']
file_path_similarity = config['path']['path_similarity']
start_file_path_image = config['path']['path_image_start']


# get data
def get_mangrove_rs():
    # check for last change
    if os.path.exists(file_path_last_change) == False:
        gt_iat = 1580915880
    else:
        gt_iat = pd.read_csv(file_path_last_change).iat[0, 2]
    # filter by gt_iat
    df_mangrove_kpi = pd.read_csv(file_path_kpi)
    df_mangrove_kpi = df_mangrove_kpi[df_mangrove_kpi['iat_original'] > gt_iat]
    list_check = df_mangrove_kpi['sub'].unique().tolist()
    # check if there are new reviews
    if len(list_check) != 0:
        # import text
        df_mangrove_text = pd.read_csv(file_path_text)
        # r'^\s*$' regular expression -> matches one or many white spaces
        df_filtered = df_mangrove_text.replace(r'^\s*$', np.nan, regex=True)
        # drop all review subjects without comments
        df_filtered.dropna(inplace=True)
        # return df
        return df_filtered


# normalise function
def normalise(df_org):
    # copy() -> creates a deep copy of the object (needed otherwise there will be some duplicates)
    df = df_org.copy()
    # normalise opinion
    def normalise_opinion(text):
        # text to lower
        text = text.lower()
        # unidecode
        text = unidecode(text)
        # tokenize opinion
        words = word_tokenize(text)
        # just keep words with letters (no punctuation, numbers, etc.)
        words = [i for i in words if i.isalpha()]
        # remove stopwords
        stop_words = set(stopwords.words('english'))
        words = [j for j in words if not j in stop_words]
        # lemmatizer
        lemmatizer = WordNetLemmatizer()
        words = [lemmatizer.lemmatize(k) for k in words]
        return words
    # function to filter out elements which occure just once
    def occure_once(text):
        words = [i for i in text if not i in hash_list_occure_once]
        return words
    # normalize text
    df['opinion'] = df['opinion'].apply(normalise_opinion)
    # create list with elements which occure just once
    list_words = list(itertools.chain.from_iterable(df['opinion']))
    hash_counter = Counter(list_words)
    hash_list_occure_once = {k for k, v in hash_counter.items() if v == 1}
    print(str(len(hash_list_occure_once))+' words (fetures) occure just once in the whole corpus, those words \
(features) will be dropped')
    # filter out elements which occure just once
    df['opinion'] = df['opinion'].apply(occure_once)
    return df


# word cloud function
def word_cloud(df_org):
    # copy() -> creates a deep copy of the object (needed otherwise there will be some duplicates)
    df = df_org.copy()
    # check for last change
    if os.path.exists(file_path_last_change) == False:
        gt_iat = 1580915880
    else:
        gt_iat = pd.read_csv(file_path_last_change).iat[0, 2]
    # filter by gt_iat
    df_mangrove_kpi = pd.read_csv(file_path_kpi)
    df_mangrove_kpi = df_mangrove_kpi[df_mangrove_kpi['iat_original']>gt_iat]
    list_check = df_mangrove_kpi['sub'].unique().tolist()
    # filter df
    df_filtered = df[df["sub"].isin(list_check)]
    # create word clouds
    count = 0
    for index, row in df_filtered.iterrows():
        # create output path by sub
        sub_full = row['sub']
        list_sub = list([i for i in sub_full if i.isalnum()])
        sub = "".join(list_sub)
        path = str(start_file_path_image)+str(sub)+'.png'
        # join list to text
        opinion = row['opinion']
        text = ' '.join([i for i in opinion])
        # create wordcloud
        wordcloud = WordCloud(width=1600, height=800, max_font_size=200, background_color="white").generate(text)
        print(str(count))
        wordcloud.to_file(path)
        count += 1
    # write last change
    gt_iat_max = df_mangrove_kpi['iat_original'].max()
    df_mangrove_kpi[df_mangrove_kpi['iat_original'] == gt_iat_max].to_csv(file_path_last_change, index=False)


# function feature extraction
def feature_extraction(df_org):
    # copy() -> creates a deep copy of the object (needed otherwise there will be some duplicates)
    df = df_org.copy()
    # get list of opinion
    list_opinion = df['opinion'].tolist()
    # feature extraction
    tfidf = TfidfVectorizer(preprocessor=' '.join)
    vectors = tfidf.fit_transform(list_opinion)
    # return vectors
    return vectors


# function cosine similarities
def cosine_similarities(matrix, df):
    cosine_similarities = linear_kernel(matrix, matrix)
    cosine_similarities = np.around(cosine_similarities, decimals=3)
    df_cosine_similarities = pd.DataFrame(data=cosine_similarities,
                                          columns=df['sub'],
                                          index=df['sub'])
    df_cosine_similarities.rename_axis(None, axis=1, inplace=True)
    df_cosine_similarities.rename_axis(None, inplace=True)
    df_cosine_similarities.to_csv(file_path_similarity, index=True)


# nlp function
def nlp_function():
    a = get_mangrove_rs()
    if a is None:
        print('no changes for similarities and wordclouds (no new reviews)')
    else:
        b = normalise(a)
        word_cloud(b)
        c = feature_extraction(b)
        cosine_similarities(c, b)
