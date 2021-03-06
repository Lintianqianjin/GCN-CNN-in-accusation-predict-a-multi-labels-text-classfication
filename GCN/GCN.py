import tensorflow as tf
import scipy.sparse as sp
import numpy as np
import tensorboard
import os
import regex as re

def load_data_npz(BaseDir):
    filenames = os.listdir(BaseDir)
    for filename in filenames:
        if filename.startswith('GCN_pointsIdx_'):
            num_Nodes = int(re.search('Idx_smaller_(?P<num_Nodes>\d*)\.', filename).group('num_Nodes'))
            break
    else:
        print('please run generatePointsIndex() first')
        return None
    adj = sp.csc_matrix(sp.load_npz(os.path.join(BaseDir,f'mapStructure.npz')),shape=(num_Nodes,num_Nodes))
    features = sp.csc_matrix(sp.load_npz(os.path.join(BaseDir,f'onehotFeatures.npz')),shape=(num_Nodes,num_Nodes))
    labels = np.load(os.path.join(BaseDir,f'labels.npy'))

    return adj, features, np.array(labels,dtype=np.float32)

def preprocess_features(features):
    """Row-normalize feature matrix and convert to tuple representation"""
    rowsum = np.array(features.sum(1))
    r_inv = np.power(rowsum, -1).flatten()
    r_inv[np.isinf(r_inv)] = 0.
    r_mat_inv = sp.diags(r_inv)
    features = r_mat_inv.dot(features)
    return features

def normalize_adj(adj):
    """Symmetrically normalize adjacency matrix."""
    adj = sp.coo_matrix(adj)
    rowsum = np.array(adj.sum(1))
    d_inv_sqrt = np.power(rowsum, -0.5).flatten()
    d_inv_sqrt[np.isinf(d_inv_sqrt)] = 0.
    d_mat_inv_sqrt = sp.diags(d_inv_sqrt)
    return adj.dot(d_mat_inv_sqrt).transpose().dot(d_mat_inv_sqrt).tocoo()


###初始化数据 开始###
adj, features,true_labels = load_data_npz(BaseDir = f'D:\CollegeCourses2019.3-2019.6\信息管理课设\code\data\GCN\smallerTest')
# print(true_labels.shape)
# exit()
features = features.tocoo()
adj = normalize_adj(adj)

features_indices = np.array([[row,col] for row,col in zip(features.row,features.col)],dtype=np.int64)
features_data = np.array([data for data in features.data],dtype=np.float32)
adj_indices = np.array([[row,col] for row,col in zip(features.row,features.col)],dtype=np.int64)
adj_data = np.array([data for data in features.data],dtype=np.float32)
###初始化数据 结束###

# print(features)
# print(support)

### 定义超参数 开始###
mapLength = 8681
num_docs = 449
gcnLayer_1_outputSize = 256
gcnLayer_2_outputSize = 64
gcnLayer_3_outputSize = 16
num_class = 5
dropout = 0.3
learning_rate = 0.005
x1_adj_input_shape = np.array([mapLength, mapLength],dtype=np.int64)
x2_features_input_shape = np.array([mapLength, mapLength],dtype=np.int64) # 一开始是onehot所以shape与邻接矩阵相同
# ### 定义超参数 结束 ###
#
# ### 定义模型输入的占位符 开始 ###
#
# x1_adj_input_shape = [mapLength, mapLength]
# x1_adj_input = tf.sparse_placeholder(tf.float32, shape=x1_adj_input_shape,name='adjMatrix')
#
# x2_features_input_shape = [mapLength, mapLength] # 一开始是onehot所以shape与邻接矩阵相同
# x2_features_input = tf.sparse_placeholder(tf.float32, shape=x2_features_input_shape,name='nodesFeaturesMatrix')
#
# labels = tf.placeholder(tf.float32,shape=(None,gcnLayer_2_outputSize),name='allNodesLabels')
# ### 定义模型输入的占位符 结束 ###
#
#
# ###第一层GCN 开始 ###
# # 定义权重矩阵
# Weight_GCN_1 = tf.Variable(tf.truncated_normal(shape=(mapLength,gcnLayer_1_outputSize), mean=0, stddev=0.1),name='gcnLayer_1_W')
# ###第一层GCN 结束 ###
#
# ###第二层GCN 开始 ###
# # 定义权重矩阵
# Weight_GCN_2 = tf.Variable(tf.truncated_normal(shape=(gcnLayer_1_outputSize,gcnLayer_2_outputSize), mean=0, stddev=0.1),name='gcnLayer_1_W')
# ###第二层GCN 结束 ###
#
# ###Dense层 开始 ###
# Weight_Dense = tf.Variable(tf.truncated_normal(shape=(gcnLayer_2_outputSize,num_class), mean=0, stddev=0.1),name='gcnLayer_1_W')
# ###Dense层 结束 ###

def add_gcnLayer(adj,features,in_size,out_size,activation_function=None,adj_sparse = True,features_sparse = False):
    if adj_sparse:
        print('adj sparse')
        adj_ordered = tf.sparse_reorder(adj)
        adj = tf.sparse.to_dense(adj_ordered)
    if features_sparse:
        print('features sparse')
        features_ordered = tf.sparse_reorder(features)
        features = tf.sparse.to_dense(features_ordered)
    print(adj)
    print(features)

    with tf.name_scope('GraphConvLayer'):
        with tf.name_scope('GraphConvLayer_W'):
            Weights = tf.Variable(tf.truncated_normal(shape=[in_size, out_size], mean=0.1, stddev=0.1))
        with tf.name_scope('GraphConvLayer_B'):
            biases = tf.Variable(tf.zeros(shape=[1,out_size])+0.01)
        with tf.name_scope('GraphConvLayer_propagate'):
            adjFeatures = tf.matmul(adj,features)
        with tf.name_scope('GraphConvLayer_conv'):
            Wx_plus_b = tf.matmul(adjFeatures,Weights) + biases
        if activation_function is None:
            outputs = Wx_plus_b
        else:
            outputs = activation_function(Wx_plus_b)
        return outputs

def add_denseLayer(features,in_size,out_size,activation_function=None):
    with tf.name_scope('DenseLayer'):
        with tf.name_scope('DenseLayer_W'):
            Weights = tf.Variable(tf.truncated_normal(shape=[in_size, out_size], mean=0.1, stddev=0.1))
        with tf.name_scope('DenseLayer_B'):
            biases = tf.Variable(tf.zeros(shape=[1, out_size]) + 0.01)
        with tf.name_scope('DenseLayer_Wx_plus_b'):
            Wx_plus_b = tf.matmul(features, Weights) + biases
        if activation_function is None:
            outputs = Wx_plus_b
        else:
            outputs = activation_function(Wx_plus_b)
        return outputs

def compute_accuracy():
    global denseLayer
    # print(sess.run(denseLayer, feed_dict={x1_adj_input: (adj_indices, adj_data, x1_adj_input_shape),
    #                                  x2_features_input: (features_indices, features_data, x2_features_input_shape),
    #                                  labels: true_labels}))
    # multiLabels = tf.nn.sigmoid(denseLayer)
    prediction = sess.run(denseLayer,feed_dict={x1_adj_input:(adj_indices, adj_data,x1_adj_input_shape),
                                   x2_features_input:(features_indices, features_data,x2_features_input_shape),
                                   labels:true_labels})
    print(prediction)
    # print(prediction)
    # print(prediction)
    # print(prediction[0])
    # print(prediction[1])
    # arr_new = np.where(prediction >= 0.6, 1.0, 0.0)
    # compare_labels = true_labels
    #
    # acc = 0
    # for index,two in enumerate(zip(arr_new,compare_labels)):
    #     if index>=499:
    #         break
    #     # print('pred')
    #     # print(two[0])
    #     # print('true')
    #     # print(two[1])
    #     if (two[0]==two[1]).all():
    #         print(f'{index}预测正确')
    #         acc+=1
    # print(acc/49)


with tf.name_scope('Inputs'):
    x1_adj_input = tf.sparse.placeholder(tf.float32,name='adjMatrixInput')
    x2_features_input = tf.sparse.placeholder(tf.float32,name='nodesFeaturesMatrixInput')

with tf.name_scope('trueLabels'):
    labels = tf.placeholder(tf.float32,shape=(8681,5),name='allNodesLabels')

gcn_layer_1 = add_gcnLayer(x1_adj_input,x2_features_input,in_size=mapLength,out_size=gcnLayer_1_outputSize,activation_function=tf.nn.tanh,features_sparse=True)
gcn_layer_2 = add_gcnLayer(x1_adj_input,gcn_layer_1,in_size=gcnLayer_1_outputSize,out_size=gcnLayer_2_outputSize,activation_function=tf.nn.tanh)
gcn_layer_3 = add_gcnLayer(x1_adj_input,gcn_layer_2,in_size=gcnLayer_2_outputSize,out_size=gcnLayer_3_outputSize,activation_function=tf.nn.tanh)
denseLayer = add_denseLayer(gcn_layer_3,in_size=gcnLayer_3_outputSize,out_size=num_class,activation_function=tf.nn.relu)

with tf.name_scope('loss'):
    loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels = tf.strided_slice(labels,[0,0],[num_docs,num_class],[1,1]),
                                            logits=tf.strided_slice(denseLayer,[0,0],[num_docs,num_class],[1,1])))
with tf.name_scope('train'):
    train_step = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)

sess = tf.Session()
# writer = tf.summary.FileWriter('D:/College Courses 2019.3-2019.6/信息管理课设/code/data/GCN/logs/',sess.graph)
sess.run(tf.global_variables_initializer())

losses = []
for i in range(32):
    print(i)
    sess.run(train_step,feed_dict={x1_adj_input:(adj_indices, adj_data,x1_adj_input_shape),
                                   x2_features_input:(features_indices, features_data,x2_features_input_shape),
                                   labels:true_labels})
    cur_loss = sess.run(loss,feed_dict={x1_adj_input:(adj_indices, adj_data,x1_adj_input_shape),
                                   x2_features_input:(features_indices, features_data,x2_features_input_shape),
                                   labels:true_labels})
    losses.append(cur_loss)
    # compute_accuracy()
    # print(sess.run())
    result = sess.run(denseLayer,feed_dict={x1_adj_input:(adj_indices, adj_data,x1_adj_input_shape),
                                       x2_features_input:(features_indices, features_data,x2_features_input_shape),
                                       labels:true_labels})
    # for j in range(1):
    #     print('result')
    #     print(result[j])
    #     print('real')
    #     print(true_labels[j])

import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.plot([i for i in range(1, len(losses) + 1)], losses, label=u'训练损失')
plt.legend()
# todo: 更换模型时要改名字
plt.savefig('GCNLOSS.png', dpi=300)
