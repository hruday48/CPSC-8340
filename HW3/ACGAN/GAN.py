
from __future__ import division
import os
import time
import tensorflow as tf
import numpy as np

from ops import *
from utils import *

from inception_score import *

from matplotlib import pyplot
import matplotlib.pyplot as plt

class GAN(object):
    model_name = "GAN"

    def __init__(self, sess, epoch, batch_size, z_dim, dataset_name, checkpoint_dir, result_dir, log_dir):
        self.sess = sess
        self.dataset_name = dataset_name
        self.checkpoint_dir = checkpoint_dir
        self.result_dir = result_dir
        self.log_dir = log_dir
        self.epoch = epoch
        self.batch_size = batch_size


        if dataset_name == 'cifar-10':
            self.data_X, self.data_y = load_cifar(self.dataset_name)

        else:
            raise NotImplementedError


        self.input_height = 32
        self.input_width = 32
        self.output_height = 32
        self.output_width = 32

        self.z_dim = z_dim
        self.c_dim = 3


        self.learning_rate_D = 0.0002
        self.learning_rate_G = 0.001
        self.learning_rate_Q = 0.0001
        self.beta1 = 0.5


        self.sample_num = 64


        self.num_batches = len(self.data_X) // self.batch_size

    def discriminator(self, x, is_training=True, reuse=False):

        with tf.variable_scope("discriminator", reuse=reuse):

            net = lrelu(conv2d(x, 64, 4, 4, 2, 2, name='d_conv1'))
            net = lrelu(bn(conv2d(net, 128, 4, 4, 2, 2, name='d_conv2'), is_training=is_training, scope='d_bn2'))
            net = lrelu(bn(conv2d(net, 256, 4, 4, 2, 2, name='d_conv3'), is_training=is_training, scope='d_bn3'))
            net = lrelu(conv2d(net, 1024, 4, 4, 4, 4, name='d_conv4'))
            net = tf.reshape(net, [self.batch_size, -1])
            out_logit = linear(net, 1, scope='d_fc5')
            out = tf.nn.sigmoid(out_logit)

            return out, out_logit, net

    def generator(self, z, is_training=True, reuse=False):

        with tf.variable_scope("generator", reuse=reuse):
            net = tf.nn.relu(bn(linear(z, 2*2*448, scope='g_fc1'), is_training=is_training, scope='g_bn1'))
            net = tf.reshape(net, [self.batch_size, 2, 2, 448])
            net = tf.nn.relu(bn(deconv2d(net, [self.batch_size, 4, 4, 256], 4, 4, 2, 2, name='g_dc2'),
                                is_training=is_training,scope='g_bn2'))
            net = tf.nn.relu(bn(deconv2d(net, [self.batch_size, 8, 8, 128], 4, 4, 2, 2, name='g_dc3'),
                                is_training=is_training, scope='g_bn3'))
            net = tf.nn.relu(bn(deconv2d(net, [self.batch_size, 16, 16, 64], 4, 4, 2, 2, name='g_dc4'),
                                is_training=is_training, scope='g_bn4'))
            out = tf.nn.sigmoid(deconv2d(net, [self.batch_size, 32, 32, 3], 4, 4, 2, 2, name='g_dc5'))

            return out

    def build_model(self):

        image_dims = [self.input_height, self.input_width, self.c_dim]
        bs = self.batch_size


        self.inputs = tf.placeholder(tf.float32, [bs] + image_dims, name='real_images')


        self.z = tf.placeholder(tf.float32, [bs, self.z_dim], name='z')




        D_real, D_real_logits, _ = self.discriminator(self.inputs, is_training=True, reuse=False)


        G = self.generator(self.z, is_training=True, reuse=False)
        D_fake, D_fake_logits, _ = self.discriminator(G, is_training=True, reuse=True)


        d_loss_real = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=D_real_logits, labels=tf.ones_like(D_real)))
        d_loss_fake = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=D_fake_logits, labels=tf.zeros_like(D_fake)))

        self.d_loss = d_loss_real + d_loss_fake


        self.g_loss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=D_fake_logits, labels=tf.ones_like(D_fake)))

        t_vars = tf.trainable_variables()
        d_vars = [var for var in t_vars if 'd_' in var.name]
        g_vars = [var for var in t_vars if 'g_' in var.name]


        with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
            self.d_optim = tf.train.AdamOptimizer(self.learning_rate_D, beta1=self.beta1) \
                      .minimize(self.d_loss, var_list=d_vars)
            self.g_optim = tf.train.AdamOptimizer(self.learning_rate_G, beta1=self.beta1) \
                      .minimize(self.g_loss, var_list=g_vars)


        self.fake_images = self.generator(self.z, is_training=False, reuse=True)

        d_loss_real_sum = tf.summary.scalar("d_loss_real", d_loss_real)
        d_loss_fake_sum = tf.summary.scalar("d_loss_fake", d_loss_fake)
        d_loss_sum = tf.summary.scalar("d_loss", self.d_loss)
        g_loss_sum = tf.summary.scalar("g_loss", self.g_loss)


        self.g_sum = tf.summary.merge([d_loss_fake_sum, g_loss_sum])
        self.d_sum = tf.summary.merge([d_loss_real_sum, d_loss_sum])

    def train(self):


        tf.global_variables_initializer().run()


        self.sample_z = np.random.uniform(-1, 1, size=(self.batch_size , self.z_dim))

        self.saver = tf.train.Saver()


        self.writer = tf.summary.FileWriter(self.log_dir + '/' + self.model_name, self.sess.graph)


        could_load, checkpoint_counter = self.load(self.checkpoint_dir)
        if could_load:
            start_epoch = (int)(checkpoint_counter / self.num_batches)
            start_batch_id = checkpoint_counter - start_epoch * self.num_batches
            counter = checkpoint_counter
            print(" [*] Load SUCCESS")
        else:
            start_epoch = 0
            start_batch_id = 0
            counter = 1
            print(" [!] Load failed...")

        IS = []


        start_time = time.time()
        for epoch in range(start_epoch, self.epoch):

        
            for idx in range(start_batch_id, self.num_batches):
                batch_images = self.data_X[idx*self.batch_size:(idx+1)*self.batch_size]
                batch_z = np.random.uniform(-1, 1, [self.batch_size, self.z_dim]).astype(np.float32)

                # update D network
                _, summary_str, d_loss = self.sess.run([self.d_optim, self.d_sum, self.d_loss],
                                               feed_dict={self.inputs: batch_images, self.z: batch_z})
                self.writer.add_summary(summary_str, counter)

                # update G network
                _, summary_str, g_loss = self.sess.run([self.g_optim, self.g_sum, self.g_loss], feed_dict={self.z: batch_z})
                self.writer.add_summary(summary_str, counter)

                # display training status
                counter += 1
                if counter%500==0:
                    print("Epoch: [%2d] [%4d/%4d] time: %4.4f, d_loss: %.8f, g_loss: %.8f" \
                      % (epoch, idx, self.num_batches, time.time() - start_time, d_loss, g_loss))

                # save training results for every 300 steps
                if np.mod(counter, 500) == 0:
                    samples = self.sess.run(self.fake_images, feed_dict={self.z: self.sample_z})
                    tot_num_samples = min(self.sample_num, self.batch_size)
                    manifold_h = int(np.floor(np.sqrt(tot_num_samples)))
                    manifold_w = int(np.floor(np.sqrt(tot_num_samples)))
                    save_images(samples[:manifold_h * manifold_w, :, :, :], [manifold_h, manifold_w],
                                './' + check_folder(self.result_dir + '/' + self.model_dir) + '/' + self.model_name + '_train_{:02d}_{:04d}.png'.format(
                                    epoch, idx))

            # After an epoch, start_batch_id is set to zero
            # non-zero value is only for the first epoch after loading pre-trained model
            start_batch_id = 0

            if epoch%5 == 0:
                # save model
                self.save(self.checkpoint_dir, counter)

               # show temporal results
                self.visualize_results(epoch)
                [a, b] = self.calculate_is()
                print('\n',a, b,'\n')
                IS.append(a)

        # save model for final step
        self.save(self.checkpoint_dir, counter)

        N = len(IS)
        x = np.linspace(0, 5 * N - 5, N)
        plt.plot(x, IS)
        plt.xlabel('epoch') #X轴标签
        plt.ylabel("IS") #Y轴标签
        plt.savefig(check_folder(self.result_dir + '/' + self.model_dir) + '/' + self.model_name + '_epoch%03d' % epoch + 'IS.png',dpi = 900)

    def visualize_results(self, epoch):
        tot_num_samples = min(self.sample_num, self.batch_size)
        image_frame_dim = int(np.floor(np.sqrt(tot_num_samples)))

        """ random condition, random noise """

        z_sample = np.random.uniform(-1, 1, size=(self.batch_size, self.z_dim))

        samples = self.sess.run(self.fake_images, feed_dict={self.z: z_sample})

        save_images(samples[:image_frame_dim * image_frame_dim, :, :, :], [image_frame_dim, image_frame_dim],
                    check_folder(self.result_dir + '/' + self.model_dir) + '/' + self.model_name + '_epoch%03d' % epoch + '_test_all_classes.png')

    def calculate_is(self):
        imgs = np.zeros((((self.batch_size*100,32,32,3))))
        for k in range(10):
            for i in range(10):
                y = np.zeros((self.batch_size, 10))
                y[:, i] = 1
                z = np.random.uniform(-1, 1, [self.batch_size, self.z_dim]).astype(np.float32)
                #z = i*0.05 + np.random.normal(loc=0.0, scale=(1.0-0.0025*i*i), size=(self.batch_size,self.z_dim))
                image = self.sess.run(self.fake_images, feed_dict = {self.z:z})
                imgs[self.batch_size*10*k+self.batch_size*i:self.batch_size*10*k+self.batch_size*i+self.batch_size,:,:,:] = image
        imgs = np.transpose(imgs, axes=[0, 3, 1, 2])
        imgs = (imgs-0.5)*2
        return (inception_score(imgs, cuda=True, batch_size=32, resize=True, splits=10))

    @property
    def model_dir(self):
        return "{}_{}_{}_{}".format(
            self.model_name, self.dataset_name,
            self.batch_size, self.z_dim)

    def save(self, checkpoint_dir, step):
        checkpoint_dir = os.path.join(checkpoint_dir, self.model_dir, self.model_name)

        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

        self.saver.save(self.sess,os.path.join(checkpoint_dir, self.model_name+'.model'), global_step=step)

    def load(self, checkpoint_dir):
        import re
        print(" [*] Reading checkpoints...")
        checkpoint_dir = os.path.join(checkpoint_dir, self.model_dir, self.model_name)

        ckpt = tf.train.get_checkpoint_state(checkpoint_dir)
        if ckpt and ckpt.model_checkpoint_path:
            ckpt_name = os.path.basename(ckpt.model_checkpoint_path)
            self.saver.restore(self.sess, os.path.join(checkpoint_dir, ckpt_name))
            counter = int(next(re.finditer("(\d+)(?!.*\d)",ckpt_name)).group(0))
            print(" [*] Success to read {}".format(ckpt_name))
            return True, counter
        else:
            print(" [*] Failed to find a checkpoint")
            return False, 0
