# -*- coding: utf-8 -*-
# For number crunching
import numpy as np
import pandas as pd

# Misc
import json 
import os
from functools import partial

# load custom libraries
import func_data as fd
import func_predictors as fp

# read parameters
import sys
validate = False
if len(sys.argv) >= 2:
    if sys.argv[1] == "validate":
        validate = True


# Load in data
activity_names = json.load(open('../public_data/annotations.json', 'r'))
class_weights = np.asarray(json.load(open('../public_data/class_weights.json', 'r')))
    
files_txt = ['L1_XGB_vH1t',
  'L1_ET_vC1t',
  'L1_NN_vD2t',
  'L1_RF_vH1t',
  'L1_NN_vA1t',
  'L1_RF_vE1t',
  'L1_ET_vH1t',
  'L1_XGB_vD1t',
  'L1_NN_vC1t']
  
all_train_x = fd.load_L1_train(files_txt)
all_train_y = fd.load_train_y([1,2,3,4,5,6,7,8,9,10])
all_train_y = all_train_y[np.isfinite(all_train_y.sum(1))]
all_test_x = fd.load_submissions(files_txt)
train_seq = fd.get_clean_sequences([1,2,3,4,5,6,7,8,9,10])
rows, tmp = fd.load_test(['ds_pir_v0'])

dataset = {'train_x':all_train_x, 'train_y':all_train_y, 'train_seq':train_seq, 'test_x':all_test_x}

# Add past data
dataset = {'train_x':np.c_[all_train_x, fd.get_past_data(all_train_x, train_seq, 1, -9999,200),
                           fd.get_past_data(all_train_x, train_seq, 2, -9999,200),
                           fd.get_future_data(all_train_x, train_seq, 1, -9999,200)], 
            'train_y':all_train_y, 
            'train_seq':train_seq, 
            'test_x':np.c_[all_test_x, fd.get_past_data(all_test_x, rows[:,0], 1, -9999),
                           fd.get_past_data(all_test_x, rows[:,0], 2, -9999),
                           fd.get_future_data(all_test_x, rows[:,0], 1, -9999)]}

# Define prediction function
def predict_model(train_x, train_y, test_x, test_y=None, class_weights=None, random_state=0):
    # Learn the ProbMC model 
    params = {'n_jobs':-1, 'random_state':random_state, 'bootstrap':False,
              'n_estimators':250, 'max_features':30, 'min_samples_leaf':1}
    model = fp.PMC_MultiTaskExtraTreesRegressor(train_y.shape[1], bags=1, params=params) 
    sample_weight = np.dot(np.power(train_y, 1), np.power(class_weights, 1))   
    model.fit(train_x, train_y, sample_weight)
    
    # Predict on the test instances
    test_predicted = model.predict_proba(test_x)
    
    params = {'n_jobs':-1, 'random_state':random_state, 'bootstrap':False,
              'n_estimators':250, 'max_features':0.75, 'min_samples_leaf':3}
    model = fp.PMC_MultiTaskExtraTreesRegressor(train_y.shape[1], bags=1, params=params) 
       
    model.fit(train_x, train_y, sample_weight)
    # Predict on the test instances
    test_predicted = test_predicted + model.predict_proba(test_x)
    
    return(test_predicted / 2)


# Set Parameters
name_to_save = 'L2_ET_vC1_0'
random_state = 1

prepbd_params = {'imputer_strategy':None}
f_preprocess = partial(fd.batch_preprocess, params=prepbd_params)

f_predict_model = partial(predict_model, random_state=random_state, class_weights=class_weights)


# Train & Predict L2_test                   
test_predicted = fp.L1_test(dataset, f_preprocess, f_predict_model, class_weights)


# Save files
directory = '../submissions/'
if not os.path.exists(directory):
    os.makedirs(directory)
# Submission
submission = pd.concat((pd.DataFrame(rows), pd.DataFrame(test_predicted)), axis=1)
submission.columns = ['record_id'] + ['start', 'end'] + activity_names
submission.to_csv('{}{}_submission.csv'.format(directory, name_to_save), index=False)

if validate:
    
    # Train & Predict L2_train
    valid_predicted, scores = fp.L1_train(dataset, f_preprocess, f_predict_model, class_weights, verbose=1)
    
    # L2_data
    valid_predicted = pd.DataFrame(valid_predicted)
    valid_predicted.columns = activity_names
    valid_predicted.to_csv('{}{}_valid.csv'.format(directory, name_to_save), index=False)
    np.savetxt('{}{}_score.csv'.format(directory, name_to_save), scores, delimiter=",")