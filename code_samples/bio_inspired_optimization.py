import numpy as np
from landscape_test_utils import landscape_function

class Particle():
    """
    Single particle as a part of the swarm, storing its position, its current function value, and the best value it has seen (pbest). The particle's velocity is based on its best found position, the best found position by the entire swarm (gbest), and its previous movement momentum. The position is subsequently updated by the velocity.
    """

    def __init__(self, upper, lower, dim, seed=1):
        # Seed allows for reproducible results but can be changed to instantiate different positions and velocities for different particles within a swarm
        np.random.seed(seed)
        # Set starting position, velocity, and best value found
        self.pos = np.random.uniform(lower, upper, dim)
        self.vel = np.random.uniform(-0.15, 0.15, dim)
        self.pbest = self.pos.copy()
        self.pbest_val = landscape_function(*self.pos)

    def update(self, r1, r2, w, c1, c2, gbest):
        # Velocity updated by previous velocity, particle's best found point, and group's best found point with weighting hyperparameters
        self.vel = w * self.vel + c1*r1*(self.pbest - self.pos) + c2*r2*(gbest - self.pos)
        # Position updated by velocity
        self.pos = self.pos + self.vel

        # Determine new position function value to check if it replaces pbest or gbest
        new_pos_val = landscape_function(*self.pos)
        if new_pos_val > self.pbest_val:
            self.pbest = self.pos
            self.pbest_val = new_pos_val

        return self.pbest, self.pbest_val


class PSO():
    """
    Swarm of particles that allows tracking of best value seen by the swarm. Each optimization step has every particle update its position, and can be run for arbitrary number of steps. Or until convergence to maxima.
    """
    def __init__(self, num_particles, dim, w, c1, c2):
        # Intialize unique particles within the swarm and store hyperparameters
        self.swarm = [Particle(-3, -1, dim, seed=i) for i in range(num_particles)]
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.dim = dim

        # Determine swarm's best found point and value
        self.gbest_val = np.max([particle.pbest_val for particle in self.swarm])
        self.gbest_loc = [particle.pbest for particle in self.swarm][np.argmax([particle.pbest_val for particle in self.swarm])]

        # Particle positions and velocities stored for graphing by timestep
        self.seen_x = [[particle.pos for particle in self.swarm]]
        self.seen_y = [[landscape_function(*particle.pos) for particle in self.swarm]]
        self.vels = [[particle.vel for particle in self.swarm]]

    def step(self):
        # Lists to store timestep positions and velocities
        curr_seen_x = []
        curr_seen_y = []
        curr_vels = []
        # Clear random seed for movement
        np.random.seed()
        r1, r2 = np.random.rand(self.dim), np.random.rand(self.dim)
        # Store best values found by particles to find best values found by the swarm
        pbest_vals = []
        pbest_locs = []
        for particle in self.swarm:
            # Update each particle's position
            pb_loc, pb_val = particle.update(r1, r2, self.w, self.c1, self.c2, self.gbest_loc)

            # Store best found points by each particle
            pbest_vals.append(pb_val)
            pbest_locs.append(pb_loc)

            curr_seen_x.append(particle.pos)
            curr_seen_y.append(landscape_function(*particle.pos))
            curr_vels.append(particle.vel)
        
        # Check if newly found points better than swarm's best found point
        best_seen_iter = np.max(curr_seen_y)
        if best_seen_iter > self.gbest_val:
            self.gbest_loc = curr_seen_x[np.argmax(curr_seen_y)]
            self.gbest_val = best_seen_iter

        self.seen_x.append(curr_seen_x)
        self.seen_y.append(curr_seen_y)
        self.vels.append(curr_vels)

    def optimize(self, num_iterations):
        # Run optimize step for arbitrary iterations
        for _ in range(num_iterations):
            self.step()

        

class Firefly():
    """
    Single firefly within the group of fireflies. It's brightness is proportional to the function value at its current position. Fireflies at each timestep are updated by moving towards the brightest neighboring firefly. Firefly brightness decays over distance with the hyperparameter light absorption, gamma. Hyperparameters alpha and beta control the degree to which the fireflies move to their brightest neighbors versus random movement.
    """
    def __init__(self, upper, lower, dim, light_absorption, base_attractiveness, alpha, seed=1):
        # Set seed for reproducible results but different fireflies within the group
        np.random.seed(seed)
        # Hyperparameter to scale random movement
        self.alpha = alpha
        self.pos = np.random.uniform(lower, upper, dim)
        self.intensity = landscape_function(*self.pos)
        # Light absorption over distance
        self.gamma = light_absorption
        # Hyperparameter to scale movement towards brightest firefly
        self.beta = base_attractiveness

    def calc_distance(self, ff):
        # Euclidean distance
        distance = np.linalg.norm(self.pos - ff.pos)
        return distance
    
    def calc_intensity(self, ff):
        # Equation to calculate intensity over distance
        distance = self.calc_distance(ff)
        intensity = ff.intensity * np.exp(-self.gamma * distance ** 2)
        return intensity
    
    def calc_attractiveness(self, ff):
        # Attractiveness scales with distance and brightness
        distance = self.calc_distance(ff)
        beta_f = self.beta / (1 + self.gamma * distance ** 2)
        return beta_f
    
    def update_position(self, ff):
        # Clear random seed
        np.random.seed()
        beta = self.calc_attractiveness(ff)
        # Update firefly location as a factor of random movement and brightest neighbor
        new_pos = self.pos + beta * (ff.pos - self.pos) + self.alpha * (np.random.rand(len(self.pos)) - 0.5)
        print((np.random.rand(len(self.pos)) - 0.5))
        # Update new position and value at that position
        self.pos = new_pos
        self.intensity = landscape_function(*self.pos)
        return new_pos

    def update_position_random(self):
        # If no brightest neighbor, move randomly
        np.random.seed()
        new_pos = self.pos + self.alpha * (np.random.rand(len(self.pos)) - 0.5) / 4
        self.pos = new_pos
        self.intensity = landscape_function(*self.pos)
        return new_pos


class FireflyOptimization():
    """
    Group of fireflies that update each firefly's position at each timestep and can be run for arbitrary timesteps or until convergence to maxima.
    """
    def __init__(self, num_fireflies, light_absorption, base_attractiveness, alpha, upper, lower, dim):
        # Store fireflies in a list, logging their position and values
        self.fireflies = [Firefly(upper, lower, dim, light_absorption, base_attractiveness, alpha, seed=i) for i in range(num_fireflies)]
        self.log_x = [[ff.pos for ff in self.fireflies]]
        self.log_y = [[ff.intensity for ff in self.fireflies]]

        # Sort fireflies by ascending brightness to update least bright fireflies first
        self.fireflies = sorted(self.fireflies, key=lambda firefly: firefly.intensity)

    def step(self):
        for ff1 in self.fireflies:
            # Find brightest neighbor and move towards
            moved = False
            for ff2 in self.fireflies:
                if ff1.intensity < ff1.calc_intensity(ff2):
                    ff1.update_position(ff2)
                    moved = True
            # Move randomly if no brightest neighbor
            if not moved:
                ff1.update_position_random()

        self.log_x.append([ff.pos for ff in self.fireflies])
        self.log_y.append([ff.intensity for ff in self.fireflies])

        # Update least bright fireflies first
        self.fireflies = sorted(self.fireflies, key=lambda firefly: firefly.intensity)

    def optimize(self, num_iterations):
        # Runs step for arbitrary iterations
        for _ in range(num_iterations):
            self.step()