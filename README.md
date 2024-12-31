# Cyber Code Portfolio - Ed Tang

## Writeups:

As an undergraduate at the United States Military Academy, I was a member and then the captain of the Cadet Competitive Cyber Team (C3T), where I competed in a variety of cybersecurity competitions both CTF and Red vs Blue format. During my time on the time, I mainly focused on Red-team related challenges and competitions. I have included the following writeups:

- `HTB_Passage`
    - Pwning HackTheBox Linux machine requiring exploiting a *CuteNews* RCE vulnerability for user access and *USBCreator* privileged read/write vulnerability to gain root access
- `OSCP_Lab_Mail`
    - Pwning a Windows machine from the OSCP training labs while I was practicing for the exam, requiring an error-based SQL injection

## Code Samples:

The first code example is from the research work for my masters thesis in data science, working to optimize engineered cardiac tissue structure with machine learning at COL Kit Parker's lab at Harvard University. Key to this research is evaluating the effectiveness of optimization algorithms on these engineering design problems. To benchmark this problem, we assume a multidimensional function `landscape_function` that maps design inputs to tissue performance, and we evaluate the efficiency of optimization algorithms in terms of finding high performance points in the least amount of points searched.

### Bio-Inspired Optimization Algorithms:

`bio_inspired_optimization.py` - Custom implementations of Particle Swarm Optimization and the Firefly Algorithm to test the efficiency of bio-inspired optimization algorithms on the test surface. Descriptions of these algorithms follow:

[Firefly Algorithm](https://link.springer.com/chapter/10.1007/978-3-642-04944-6_14):

The firefly algorithm is a bio-inspired optimization algorithm that mimics the behavior of mating fireflies that are attracted to one another through their bioluminescent glow. The algorithm makes the following assumptions: (1) Fireflies are unisex and attracted to all other fireflies. (2) Fireflies are attracted to others proportional to brightness, where less bright fireflies are attracted to brighter fireflies. (3) If a firefly is not near a brighter firefly, it will move randomly. (4) Firefly brightness is based on the fitness at its location in the parameter space. After random initialization of fireflies, during each iteration, each firefly’s position gets updated based on these rules, until convergence. 

[Particle Swarm Optimization](https://ieeexplore.ieee.org/document/488968):

Particle swarm optimization is a different bio-inspired optimization algorithm representing decision-making from the aggregate of the collective information from a group of organisms, such as fish or birds. The algorithm starts by randomly initializing particles within the search space, along with a randomized velocity vector. 

The velocity vector is updated at each timestep as a linear combination of the original velocity , a vector towards the highest fitness point seen by the particle, and a vector towards the highest fitness point seen by the swarm. Hyperparameters balance exploration and exploitation by weighting the initial velocity, vector towards particle’s best point, and vector towards swarm’s best point respectively. 

### Bayesian Optimization With Neural Network Ensembles:

`custom_nn_bayes.py` - Custom implementation of Bayesian Optimization with neural networks for a similar optimization task. Bayesian Optimization functions by training a model to predict the function, and with each timestep, new points are searched based on an acquisition functions, which balances exploration and exploitation (predicted values and uncertainty), and these searched points are evaluated and used to retrain the model, with the model iteratively gaining a better understanding of the function and finding higher value points. 

Since Bayesian Optimization iteratively searches points based on predicted values and uncertainty, when using an ensemble of neural networks with different random initializations, the mean predictions can serve as the prediction, while the prediction standard deviation can serve as uncertainty. This method leverages the power of neural networks for representing high dimensional data and applies it to the optimization method. In this implementation, subsequent points are sampled by the Upper Confidence Bound (UCB) acquistion function from a large pseudorandomly generated sample set. 
