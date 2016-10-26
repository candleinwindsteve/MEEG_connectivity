# -*- coding: utf-8 -*-
import numpy as np
import sys
import scipy.io

import matplotlib.pyplot as plt

# no depth weithing is reapplied to the source solution

# for portability, I need to make write it as a package
path = "/home/ying/Dropbox/MEG_source_loc_proj/source_roi_cov/"
sys.path.insert(0, path)
from ROI_Kalman_smoothing import (get_param_given_u, simulate_kalman_filter_data)


# directly estimate Ath for u_t+h = Ath u_t + error
# with ordinary least square retression
def least_square_lagged_regression(u_array):
    """
    u_array, q, T+1, p
    """
    q,T,p = u_array.shape
    T -= 1
    # t0, t1 term is t1 regressed on t0
    lagged_coef_mat = np.zeros([T,T],dtype = np.object)
    for t0 in range(T):
        for t1 in range(t0,T):
            tmp_coef = np.zeros([p,p])
            for i in range(p):
                # least square regression u_t+h[i]  u_t
                tmp_y = u_array[:,t1+1,i]
                tmp_x = u_array[:,t0,:]
                # (X'X)^{-1} X' Y
                tmp_coef[i,:] = np.linalg.inv(tmp_x.T.dot(tmp_x)).dot(tmp_x.T.dot(tmp_y))
                
            lagged_coef_mat[t0,t1] = tmp_coef
                
    return lagged_coef_mat

def get_tilde_A_from_At(A):
    """
        A[T,p,p]
    """
    tilde_A = np.zeros([T,T], dtype = np.object)  
    for i0 in range(T):
        tilde_A[i0,i0] = A[i0].copy()
    for i0 in range(T):
        for j0 in range(i0+1,T):
            tmp = np.eye(p)
            for l0 in range(j0,i0-1,-1):
                tmp = (np.dot(tmp, A[l0])).copy()
            tilde_A[i0,j0] = tmp
    return tilde_A
    
def get_dynamic_linear_coef(tildeA, pair):
    T = tildeA.shape[0]
    tilde_A_entry = np.zeros([T,T])
    for t1 in range(T):
        for t2 in range(T):
            if t1<= t2:
                tilde_A_entry[t1,t2] = tildeA[t1,t2][pair[1], pair[0]]
            else:
                # region 2 -> region 1 lower diangonal feedback
                tilde_A_entry[t1,t2] = tildeA[t2,t1][pair[0], pair[1]] 
    
    return tilde_A_entry
#============================    
    
if __name__ == "__main__":
    
    
    T = 200
    p = 2
    
    #=====================
    # create AR 1 model, sanity check
    time_covar = np.zeros([T, T], dtype = np.float)
    a = 1e-3
    for i in range(T):
        for j in range(T):
            time_covar[i,j] = np.exp(- a*(i-j)**2)
            if i == j:
                time_covar[i,j] *= 1.01
    A = np.zeros([T,p,p])
    for i in range(p):
        for j in range(p):
            A[:, i,j] += np.random.multivariate_normal(np.zeros(T, dtype= np.float), time_covar)
    
    A[:,0,1] = 0.0
    #A[:,0,0] = 0.1
    #A[:,1,1] = 0.1
    # normalize A 
    A /= np.max(np.abs(A))
    Q0 = np.eye(p) 
    Q = np.eye(p)
    C = np.eye(p)
    R = np.eye(p)
    n_trial = 100        
    #u_data, _ = simulate_kalman_filter_data(T, Q0, A, Q, C, R, n_trial)
    #========================
    # long lag dependence in u
    #  AR pp model
    
    pp = 5
    A_list = np.zeros(pp, dtype = np.object)
    for l in range(pp):
        A_list[l] =  A*2.0*(np.random.rand(1)-0.5) + np.random.randn(T,p,p)*0.1
        A_list[l][:,0,1] = 0.0
    u_data1 = np.zeros([n_trial, T+1, p])
    for r in range(n_trial):
        # first pp time points
        u_data1[r,0,:] = np.random.multivariate_normal(np.zeros(p), Q0)
        for t in range(1, T+1):
            tmp_max = t if t< pp else pp
            tmp = np.random.multivariate_normal(np.zeros(p), Q)
            for t1 in range(0,tmp_max):
                # A 1:T+1 starts with 0, so do t-1
                # if there are pp terms, go over all of them
                # otherwise go until t-1
                tmp += A_list[t1][t-1].dot(u_data1[r,t-t1-1,:])
                
            u_data1[r,t,:]= tmp
            
    u_data = u_data1.copy()
           
    #================================================        
    # solution
    Gamma0_0 = np.eye(p)
    A_0 = np.zeros([T,p,p])
    Gamma_0 = np.eye(p)
    # first run the non_prior version to get a global solution
    Gamma0_1, A_1, Gamma_1 = get_param_given_u(u_data, Gamma0_0, A_0, Gamma_0, 
       flag_A_time_vary = True,
       prior_Q0 = None, prior_A = None, prior_Q = None)
    tildeA1 = get_tilde_A_from_At(A_1)
    tildeA2 = least_square_lagged_regression(u_data)
    
    pair = [0,1]
    tildeA_entry1 = np.abs(get_dynamic_linear_coef(tildeA1, pair))
    tildeA_entry2 = np.abs(get_dynamic_linear_coef(tildeA2, pair))
       
    
    
    #=============================================================
    plt.figure()
    for i1 in range(p):
        for i2 in range(p):
            plt.subplot(p,p, i1*p+i2+1)
            plt.plot(A[:,i1,i2])
            plt.plot(A_1[:,i1,i2])
            plt.title("%d %d" %(i1,i2))
            

    vmin,vmax = None, None
    plt.figure()
    to_plot = [tildeA_entry1, tildeA_entry2, tildeA_entry2-tildeA_entry1]
    for l in range(len(to_plot)):
        plt.subplot(1,len(to_plot),l+1)
        plt.imshow(to_plot[l], interpolation = "none", vmin = vmin, vmax = vmax,
                   aspect = "auto",
                   extent = [0,T,0,T], origin = "lower")
        plt.xlabel(pair[1])
        plt.ylabel(pair[0])
        plt.colorbar()

