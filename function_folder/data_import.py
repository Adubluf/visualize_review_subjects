import pandas as pd
from configparser import ConfigParser

# load config
config = ConfigParser()
config.read('config/config.ini')

# load path
path_business = config['path']['path_business']
path_kpi = config['path']['path_kpi']
path_similarity = config['path']['path_similarity']


# import data
def load_data():
    # load dataset
    business = pd.read_csv(path_business)
    kpi = pd.read_csv(path_kpi)
    similarity = pd.read_csv(path_similarity, index_col=0)
    # datasets to json
    datasets = {'business': business.to_json(orient='split'),
                'kpi': kpi.to_json(orient='split'),
                'similarity': similarity.to_json(orient='split')}
    return datasets
