import tensorflow as tf
import numpy as np
from tensorflow.keras import layers, models
from sklearn.metrics import mean_squared_error
from scipy.stats import qmc
from landscape_test_utils import landscape_function, BOUNDS_10D_LOCAL


def sample_LHC(samples, dims, seed=None):
    # Latin Hypercube pseudorandom sampling for neural network sampling
    lhs = qmc.LatinHypercube(d=dims, seed=seed)
    sample = lhs.random(n=samples)
    return np.array(sample)


# Functions to create TF models for simple FCNNs and RNNs with similar trainable parameter counts for evaluation
def create_rnn(dim):
    model = models.Sequential([
        layers.Input(shape=(dim, 1)), 
        layers.LSTM(32, return_sequences=True),
        layers.LSTM(16, return_sequences=True), 
        layers.LSTM(8), 
        layers.Dense(1)  
    ])
    model.compile(optimizer='adam', loss='mse')

    return model

def create_ffnn(dim):
    model = models.Sequential([
        layers.Input(shape=(dim,)),
        layers.Dense(128, activation='relu'),
        layers.Dense(64, activation='relu'),
        layers.Dense(32, activation='relu'),
        layers.Dense(1)
    ])  
    model.compile(optimizer='adam', loss='mse')
    return model

def scale_samples(samples, lower, upper):
    return lower + (upper - lower) * samples

# Acquisition function balances exploration and exploitation with parameter kappa, weighting the importance of ensemble prediction mean and standard deviation (predictions vs uncertainty)
def ucb(predictions, kappa=2.576):
    mu = np.mean(predictions, axis=0)
    sig = np.std(predictions, axis=0)
    return mu + kappa * sig

# Standardize data for input into NNs
def standardize_input(input_vec, bounds):
    standardized = np.zeros_like(input_vec)
    for dim in range(input_vec.shape[1]):
        lower_bound, upper_bound = bounds[dim]
        mean = (lower_bound + upper_bound) / 2
        std = upper_bound - mean
        standardized[:, dim] = (input_vec[:, dim] - mean) / std
    return standardized

# Train ensemble for 1 cycle
def train_ensemble_LHS_bayes_local(ensemble, epochs, batch_size, X_trains, y_trains, ucb_k, seed=0, landscape_seed=42):
    trained_ensemble = []
    # Pseudorandomly sample points and preprocess
    sample_X = sample_LHC(batch_size*10000, 10, seed=seed+landscape_seed)
    sample_X = scale_samples(sample_X, -3, -1)
    sample_X_std = standardize_input(sample_X, BOUNDS_10D_LOCAL)

    lhs_preds = []
    for model in ensemble:
        # Predict on sampled points
        prediction = model.predict(sample_X_std)
        lhs_preds.append(prediction)
    
    # Evaluate acquisition function
    ucb_vals = ucb(lhs_preds, kappa=ucb_k)

    # Find points with highest uncertainty and predictions to become the iteration's searched points
    top_ucb_inds = np.argsort(ucb_vals.ravel())[-batch_size:].ravel()

    X_train = sample_X_std[top_ucb_inds]
    
    X_train_unscaled = sample_X[top_ucb_inds]
    # Evaluate the searched points
    y_train = landscape_function(X_train_unscaled[:,0], X_train_unscaled[:,1], X_train_unscaled[:,2], X_train_unscaled[:,3],
                                X_train_unscaled[:,4], X_train_unscaled[:,5], X_train_unscaled[:,6], X_train_unscaled[:,7],
                                X_train_unscaled[:,8], X_train_unscaled[:,9], seed=landscape_seed)
    
    for model in ensemble:
        # Train each model in the ensemble on the searched points
        model.fit(np.array(X_train), np.array(y_train), epochs=epochs, verbose=0)
        trained_ensemble.append(model)

    X_trains.append(sample_X)
    y_trains.append(y_train)

    return trained_ensemble, X_trains, y_trains

def set_seed(seed):
    tf.random.set_seed(seed)
    np.random.seed(seed)
    
# Function to pretrain the model with a small sample size to prevent high variance in ensemble predictions in early training cycles   
def warm_start_model(model, batch_size, landscape_seed=1, epochs=50):
    sample_X = sample_LHC(batch_size, 10, seed=0)
    
    sample_X = scale_samples(sample_X, -3, -1)
        
    sample_X_std = standardize_input(sample_X, BOUNDS_10D_LOCAL)
    
    X_train = sample_X_std
    y_train = landscape_function(sample_X[:,0], sample_X[:,1], sample_X[:,2], sample_X[:,3],
                                    sample_X[:,4], sample_X[:,5], sample_X[:,6], sample_X[:,7],
                                    sample_X[:,8], sample_X[:,9], seed=landscape_seed)
    model.fit(np.array(X_train), np.array(y_train), epochs=epochs, verbose=0)
    
    return model, [sample_X], [y_train]



if __name__ == "__main__":

    num_nets = 10
    epochs = 25
    batch_size = 16

    global_x_train = []
    global_y_train = []
    global_ensembles = []

    # Evaluate on 5 different landscapes
    for landscape_seed in range(1, 6):

        ensemble = []

        # Initialize models in the ensemble with warm started training data
        for i in range(num_nets):
            set_seed(i)
            model = create_ffnn(10)
            model, x_init, y_init = warm_start_model(model, 128, landscape_seed=landscape_seed)
            ensemble.append(model)
            print(np.max(y_init))

        X_trains, y_trains = x_init, y_init
        
        # Initial kappa value favoring exploration
        ucb_k = 2.576
        
        y_trains = np.array(y_trains).reshape((-1, batch_size)).tolist()

        for i in range(2176//batch_size):
            # Kappa decays every training cycle to encourage exploitation as the search continues
            curr_ucb_k = ucb_k * np.exp(-0.15*i)
            ensemble, X_trains, y_trains = train_ensemble_LHS_bayes_local(ensemble, epochs, batch_size, X_trains, y_trains, curr_ucb_k, seed=i, landscape_seed=landscape_seed)

        global_x_train.append(X_trains)
        global_y_train.append(y_trains)
        
        global_ensembles.append(ensemble)
    
    # Save results
    np.save("./bayes_rnn_ensemble_xtrain_LHS_combined.npy", global_x_train)
    np.save("./bayes_rnn_ensemble_ytrain_LHS_combined.npy", global_y_train)

    # Save models
    for i in range(len(global_ensembles)):
        ensemble = global_ensembles[i]
        for j in range(len(ensemble)):
            ensemble[j].save(f"./bayes_rnn_{i}_{j}.keras")