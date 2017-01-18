# -*- coding: UTF-8 -*-

import math
import numpy as np
import tensorflow as tf

DEBUG = True
MAX_EPOCHS = 1000000000
PRECISON = 0.0000001
N = 100
DATA_MEAN = 5
THRESHOLD =  1e-6

# np.random.seed(7)

# TODO: Adjust learning rates
# Learning rates
#        a     b    mu   beta
lrs = [1e-3, 1e-3, 1.0, 1.0]

# Data generation
xn = tf.convert_to_tensor(np.random.normal(DATA_MEAN, 1, N), dtype=tf.float64)

m = tf.Variable(0., dtype=tf.float64)
beta = tf.Variable(0.0001, dtype=tf.float64)
a = tf.Variable(0.001, dtype=tf.float64)
b = tf.Variable(0.001, dtype=tf.float64)

# Needed for variational initilizations
a_gamma_ini = np.random.gamma(1, 1, 1)[0]
b_gamma_ini = np.random.gamma(1, 1, 1)[0]

# Variational parameters
a_gamma_var = tf.Variable(a_gamma_ini, dtype=tf.float64)
b_gamma_var = tf.Variable(b_gamma_ini, dtype=tf.float64)
m_mu = tf.Variable(np.random.normal(0., (0.0001)**(-1.), 1)[0], dtype=tf.float64)
beta_mu_var = tf.Variable(np.random.gamma(a_gamma_ini, b_gamma_ini, 1)[0], dtype=tf.float64)

# Maintain numerical stability
a_gamma = tf.add(tf.nn.softplus(a_gamma_var), PRECISON)
b_gamma = tf.add(tf.nn.softplus(b_gamma_var), PRECISON)
beta_mu = tf.add(tf.nn.softplus(beta_mu_var), PRECISON)

# Lower Bound definition
LB = tf.mul(tf.cast(1./2, tf.float64), tf.log(tf.div(beta, beta_mu)))
LB = tf.add(LB, tf.mul(tf.mul(tf.cast(1./2, tf.float64), tf.add(tf.pow(m_mu, 2), tf.div(tf.cast(1., tf.float64), beta_mu))), tf.sub(beta_mu, beta)))
LB = tf.sub(LB, tf.mul(m_mu, tf.sub(tf.mul(beta_mu, m_mu), tf.mul(beta, m))))
LB = tf.add(LB, tf.mul(tf.cast(1./2, tf.float64), tf.sub(tf.mul(beta_mu, tf.pow(m_mu, 2)), tf.mul(beta, tf.pow(m, 2)))))

LB = tf.add(LB, tf.mul(a, tf.log(b)))
LB = tf.sub(LB, tf.mul(a_gamma, tf.log(b_gamma)))
LB = tf.add(LB, tf.lgamma(a_gamma))
LB = tf.sub(LB, tf.lgamma(a))
LB = tf.add(LB, tf.mul(tf.sub(tf.digamma(a_gamma), tf.log(b_gamma)), tf.sub(a, a_gamma)))
LB = tf.add(LB, tf.mul(tf.div(a_gamma, b_gamma), tf.sub(b_gamma, b)))

LB = tf.add(LB, tf.mul(tf.div(tf.cast(N, tf.float64), tf.cast(2., tf.float64)), tf.sub(tf.digamma(a_gamma), tf.log(b_gamma))))
LB = tf.sub(LB, tf.mul(tf.div(tf.cast(N, tf.float64), tf.cast(2., tf.float64)), tf.log(tf.mul(tf.cast(2., tf.float64), math.pi))))
LB = tf.sub(LB, tf.mul(tf.cast(1./2, tf.float64), tf.mul(tf.div(a_gamma, b_gamma), tf.reduce_sum(tf.pow(xn, 2)))))
LB = tf.add(LB, tf.mul(tf.div(a_gamma, b_gamma), tf.mul(tf.reduce_sum(xn), m_mu)))
LB = tf.sub(LB, tf.mul(tf.div(tf.cast(N, tf.float64), tf.cast(2., tf.float64)), tf.mul(tf.div(a_gamma, b_gamma), tf.add(tf.pow(m_mu, 2), tf.div(tf.cast(1., tf.float64), beta_mu)))))

# Optimizer definition (Coordinate ascent simulation)
mode = tf.placeholder(tf.int32, shape=[], name='mode')
learning_rate = tf.placeholder(tf.float32, shape=[], name='learning_rate')
optimizer = tf.train.GradientDescentOptimizer(learning_rate=learning_rate)
grads_and_vars = None
def f0(): 
	grads_and_vars = optimizer.compute_gradients(-LB, var_list=[a_gamma_var])
	return optimizer.apply_gradients(grads_and_vars)
def f1(): 
	grads_and_vars = optimizer.compute_gradients(-LB, var_list=[b_gamma_var])
	return optimizer.apply_gradients(grads_and_vars)
def f2(): 
	grads_and_vars = optimizer.compute_gradients(-LB, var_list=[m_mu])
	return optimizer.apply_gradients(grads_and_vars)
def f3(): 
	grads_and_vars = optimizer.compute_gradients(-LB, var_list=[beta_mu_var])
	return optimizer.apply_gradients(grads_and_vars)
train = tf.case({tf.cast(mode==0, dtype=tf.bool): f0, 
				 tf.cast(mode==1, dtype=tf.bool): f1, 
				 tf.cast(mode==2, dtype=tf.bool): f2, 
				 tf.cast(mode==3, dtype=tf.bool): f3}, 
				default=f0, exclusive=True)

# Summaries definition
tf.summary.histogram('m_mu', m_mu)
tf.summary.histogram('beta_mu', beta_mu)
tf.summary.histogram('a_gamma', a_gamma)
tf.summary.histogram('b_gamma', b_gamma)
merged = tf.summary.merge_all()
file_writer = tf.summary.FileWriter('/tmp/tensorboard/', tf.get_default_graph())
run_calls = 0

# Main program
init = tf.global_variables_initializer()
with tf.Session() as sess:
	sess.run(init)
	for epoch in xrange(MAX_EPOCHS):
		
		# Parameter updates
		sess.run(train, feed_dict={mode: 0, learning_rate: lrs[0]})
		sess.run(train, feed_dict={mode: 1, learning_rate: lrs[1]})
		sess.run(train, feed_dict={mode: 2, learning_rate: lrs[2] * epoch/100})
		sess.run(train, feed_dict={mode: 3, learning_rate: lrs[3]})

		# ELBO computation
		mer, lb, mu_out, beta_out, a_out, b_out = sess.run([merged, LB, m_mu, beta_mu_var, a_gamma_var, b_gamma_var])
		print('Epoch {}: Mu={} Precision={} ELBO={}'.format(epoch, mu_out, a_out/b_out, lb))
		run_calls += 1
		file_writer.add_summary(mer, run_calls)
		
		# Break condition
		if epoch > 0: 
			if abs(lb-old_lb) < THRESHOLD:
				break
		old_lb = lb