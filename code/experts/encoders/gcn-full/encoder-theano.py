import numpy as np
import theano
from theano import tensor as T
from scipy.sparse import csr_matrix, coo_matrix
import scipy.sparse as sps
import scipy
import imp

abstract = imp.load_source('abstract_encoder', 'code/experts/encoders/abstract_message_based_graph_encoder.py')

class Encoder(abstract.TheanoEncoder):

    settings = None
    vertex_embedding = None
    
    def __init__(self, encoder_settings):
        self.settings = encoder_settings

        self.entity_count = int(self.settings['EntityCount'])
        self.relation_count = int(self.settings['RelationCount'])
        self.embedding_width = int(self.settings['EmbeddingWidth'])
        self.n_convolutions = int(self.settings['NumberOfConvolutions'])    

    
    def initialize_test(self):
        self.X = T.matrix('X', dtype='int32')
    
    def initialize_train(self):
        embedding_initial = np.random.randn(self.entity_count, self.embedding_width).astype(np.float32)        
        relation_initial = np.random.randn(self.relation_count, self.embedding_width).astype(np.float32)
        type_initials = [np.random.randn(self.relation_count*2+1, self.embedding_width, self.embedding_width).astype(np.float32)
                                for _ in range(self.n_convolutions)]

        self.X = T.matrix('X', dtype='int32')

        self.W_embedding = theano.shared(embedding_initial)
        self.W_relation = theano.shared(relation_initial)
        self.W_types = [theano.shared(t) for t in type_initials]
        
    def get_vertex_embedding(self, training=False):
        activated_embedding = self.W_embedding

        for W_type in self.W_types:
            #Fetch 
            MessageTransforms = W_type[self.E_to_R]

            #Gather values from vertices in message matrix:
            MessageValues = activated_embedding[self.E_to_V]
            Messages = T.batched_dot(MessageTransforms, MessageValues)

            mean_messages = theano.sparse.dot(self.V_to_E, Messages)

            vertex_embedding = mean_messages
            activated_embedding = T.nnet.relu(mean_messages)

        #No activation for final layer:
        self.vertex_embedding = vertex_embedding
        
    def get_all_subject_codes(self):
        if self.vertex_embedding is None:
            self.get_vertex_embedding()
            
        return self.vertex_embedding
    
    def get_all_object_codes(self):
        if self.vertex_embedding is None:
            self.get_vertex_embedding()

        return self.vertex_embedding
    
    def get_weights(self):
        return [self.W_embedding, self.W_relation] + self.W_types

    def get_input_variables(self):
        return [self.X]

    def encode(self, training=True):
        if self.vertex_embedding is None:
            self.get_vertex_embedding()
            
        self.e1s = self.vertex_embedding[self.X[:,0]]
        self.rs = self.W_relation[self.X[:,1]]
        self.e2s = self.vertex_embedding[self.X[:,2]]

        return self.e1s, self.rs, self.e2s

    def get_regularization(self):
        #regularization = tf.reduce_mean(tf.square(self.e1s))
        #regularization += tf.reduce_mean(tf.square(self.rs))
        #regularization += tf.reduce_mean(tf.square(self.e2s))

        return 0 #self.regularization_parameter * regularization

    def parameter_count(self):
        return 2 + self.n_convolutions

    
    def assign_weights(self, weights):
        self.W_embedding = theano.shared(weights[0])
        self.W_relation = theano.shared(weights[1])
        self.W_types = [theano.shared(w) for w in weights[2:]]
