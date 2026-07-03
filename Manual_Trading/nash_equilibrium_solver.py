import numpy as np
from scipy.optimize import fsolve

def solve_x(z):
    """
    Find the optimal Research percentage (X) for a given Speed percentage (Z).
    The remaining budget (100 - Z - X) will be assigned to Scale (Y).
    Equation: (1+X)*(1+ln(1+X)) = 101 - Z
    """
    def eq(x):
        return (1+x)*(1+np.log(1+x)) - (101 - z)
    
    # Use a safe initial guess
    x_opt = fsolve(eq, 10.0)[0]
    return x_opt

def get_W(z):
    """
    Calculate the Base Product W(Z) = Research(X) * Scale(Y)
    given the optimal split for Z.
    """
    x = solve_x(z)
    y = 100 - z - x
    r = (200000 / np.log(101)) * np.log(1 + x)
    s = 0.07 * y
    return r * s, x, y

def main():
    print("--- ROUND 2: INVEST & EXPAND NASH EQUILIBRIUM SOLVER ---\n")
    
    # Get base product at Z=0
    W0, x0, y0 = get_W(0)
    
    # Find the maximum rational bid Z_max where F(Z) = 1.0
    def max_z_eq(z_guess):
        w_val, _, _ = get_W(z_guess[0])
        return w_val - (W0 / 9)
    
    z_max = fsolve(max_z_eq, 80.0)[0]
    print(f"Maximum Rational Speed Bid (Z_max): {z_max:.2f}%\n")
    
    # Sample a pure strategy from the mixed Nash Equilibrium distribution
    print("Generating a mathematically unexploitable strategy play...")
    
    # Randomly draw a cumulative probability F(Z) between 0 and 1
    random_prob = np.random.uniform(0, 1)
    
    # Find the Speed (Z) that matches this probability
    # Formula: F(Z) = (1/8) * ((W0 / W(Z)) - 1)
    # Target: F(Z) - random_prob = 0
    def sample_eq(z_guess):
        w_val, _, _ = get_W(z_guess[0])
        fz = (1/8) * ((W0 / w_val) - 1)
        return fz - random_prob
        
    # Solve for the sampled Z
    sampled_z = fsolve(sample_eq, 40.0)[0]
    
    # Get the corresponding optimal X and Y
    _, sampled_x, sampled_y = get_W(sampled_z)
    
    print(f"Randomly drawn percentile: {random_prob*100:.1f}%")
    print(f"\n>>> RECOMMENDED NASH EQUILIBRIUM PLAY <<<")
    print(f"Research (X): {sampled_x:.2f}%")
    print(f"Scale (Y):    {sampled_y:.2f}%")
    print(f"Speed (Z):    {sampled_z:.2f}%")
    print(f"-----------------------------------------")
    print(f"Sum = {sampled_x + sampled_y + sampled_z:.2f}% (Exactly 100% Budget Used)")

if __name__ == "__main__":
    main()
