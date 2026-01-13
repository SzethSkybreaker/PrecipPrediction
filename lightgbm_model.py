import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score as ras
import os

#dataset of format specified in combine_snd_sfc.py read into pandas dataframe
df = pd.read_csv(os.path.join('.','ultimate_dataset2.csv'))

#create label and target datasets for model to train on
features = df.drop('precip_type', axis=1)
features = features.drop('date',axis=1)
target = df['precip_type']

#split dataset 80/20 into training and validation dataset
X_train, X_val, Y_train, Y_val = train_test_split(features, target, test_size=0.2, random_state=2023)

#put into dataset which lgbm can use
train_data = lgb.Dataset(X_train, label=Y_train)
test_data = lgb.Dataset(X_val, label=Y_val, reference=train_data)

#choose training parameters
# objective: binary choice, rain or snow
# metric: how to evaluate model, tells you the probability given a random data point, that the model correctly classifies it
# boosting_type: gradient boosted tree
# num_leaves: how large a decision tree gets
# learning_rate: the weight given to each tree
# feature_fraction: 
# early_stopping_round: earliest the model will stop if AUC is low
# I couldn't tell you the theory behind this well, but I tweaked this till I got good results

params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 8,
    'learning_rate': 0.01,
    'feature_fraction': 0.9,
    #'max_depth':6, 
    'early_stopping_round':40
}

#maximum number of rounds to train for. Thus, model will train between 40 and 100 rounds
num_round = 100
#train the model
bst = lgb.train(params, train_data, num_round, valid_sets=[test_data])

#make predictions on training and validation datasets
y_train = bst.predict(X_train)
y_val = bst.predict(X_val)

#compare to the classifiers, how well did we do? 
y_train_class = (y_train > 0.5).astype(int)
y_val_class = (y_val > 0.5).astype(int)

#print results
print("Training ROC-AUC: ", ras(Y_train, y_train))
print("Validation ROC-AUC: ", ras(Y_val, y_val))

#create, save, and then load a model
bst.save_model('lightgbm_model.txt') 
#loaded_model = lgb.Booster(model_file='lightgbm_model.txt') 